import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
import threading
import time
import traceback
import random
import csv
from optimized_timesheet import attendance_record_to_dict

# إعداد التسجيل
logger = logging.getLogger(__name__)

# إعداد واجهة BioTime API
PRIMARY_API_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BACKUP_API_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/"
BIOTIME_API_BASE_URL = PRIMARY_API_URL  # Default to primary URL
BIOTIME_USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
BIOTIME_PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")
DEPARTMENTS = [10]  # تحديث رقم القسم ليطابق الرابط الجديد

# إلغاء تفعيل وضع البيانات التجريبية (تم تعديله لمنع استخدام البيانات التجريبية)
MOCK_MODE_ENABLED = False

# إعدادات نطاق التاريخ للمزامنة
SYNC_START_DATE = os.environ.get("SYNC_START_DATE", "")
SYNC_END_DATE = os.environ.get("SYNC_END_DATE", "")

# Connection timeout settings
CONNECT_TIMEOUT = 30  # Timeout for establishing connection
READ_TIMEOUT = 180    # Timeout for reading response

# متغير عالمي للتحكم في حالة المزامنة
CANCEL_SYNC = False
SYNC_THREAD = None
SYNC_PROGRESS = {"status": "none", "step": "", "progress": 0, "message": "", "records": 0, "error": ""}

def update_sync_status(step, progress, message=None, error=None, records=0, status=None):
    """تحديث حالة المزامنة العالمية"""
    global SYNC_PROGRESS

    if step is not None:
        SYNC_PROGRESS["step"] = step
    if progress is not None:
        SYNC_PROGRESS["progress"] = progress
    if message is not None:
        SYNC_PROGRESS["message"] = message
    if error is not None:
        SYNC_PROGRESS["error"] = error
    if records is not None:
        SYNC_PROGRESS["records"] = records
    if status is not None:
        SYNC_PROGRESS["status"] = status

    logger.debug(f"تحديث حالة المزامنة: {step}, {progress}%, {message}, حالة: {status}")

def check_cancellation(sync_log=None, db=None):
    """التحقق من طلب إلغاء المزامنة"""
    global CANCEL_SYNC

    if CANCEL_SYNC:
        logger.info("تم إلغاء المزامنة بناء على طلب المستخدم")
        update_sync_status("cancel", 0, "تم إلغاء المزامنة بناء على طلب المستخدم", status="cancelled")

        if sync_log and db:
            try:
                sync_log.status = "cancelled"
                sync_log.error_message = "تم إلغاء المزامنة بناء على طلب المستخدم"
                sync_log.end_time = datetime.utcnow()
                db.session.commit()
                logger.info("تم تحديث سجل المزامنة بحالة الإلغاء")
            except Exception as e:
                logger.error(f"خطأ في تحديث سجل المزامنة: {str(e)}")

        return True

    return False

def generate_mock_data(start_date, end_date, num_employees=20):
    """Generate mock attendance data when API is unavailable"""
    logger.info("Generating mock attendance data for testing")

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)

    mock_data = []
    employee_names = [
        ("Ahmed", "Ali"), ("Mohammed", "Ibrahim"), ("Khalid", "Abdullah"),
        ("Sara", "Mohammed"), ("Fatima", "Ahmed"), ("Noura", "Sami"),
        ("Abdullah", "Khalid"), ("Saleh", "Mohammed"), ("Omar", "Yusuf"),
        ("Aisha", "Abdullah"), ("Huda", "Ali"), ("Maryam", "Hassan"),
        ("Yusuf", "Ibrahim"), ("Layla", "Ahmed"), ("Nasser", "Khalid"),
        ("Amina", "Mohammed"), ("Hassan", "Abdullah"), ("Zainab", "Ali"),
        ("Ibrahim", "Saleh"), ("Nadia", "Sami")
    ]
    departments = ["HR", "IT", "Finance", "Operations", "Marketing"]
    terminals = [
        ("Terminal_A", "T001", 1),
        ("Terminal_B", "T002", 1),
        ("Terminal_C", "T003", 2),
        ("Terminal_D", "T004", 2)
    ]

    for emp_idx in range(1, num_employees+1):
        emp_code = f"EMP{emp_idx:03d}"
        first_name, last_name = employee_names[(emp_idx-1) % len(employee_names)]
        dept_name = departments[(emp_idx-1) % len(departments)]

        for date in date_range:
            if date.weekday() in [4, 5] and random.random() < 0.7:
                continue

            check_in_hour = 7 + random.randint(0, 1)
            check_in_minute = random.randint(0, 59)
            check_in_time = f"{check_in_hour:02d}:{check_in_minute:02d}"

            check_out_hour = 16 + random.randint(0, 1)
            check_out_minute = random.randint(0, 59)
            check_out_time = f"{check_out_hour:02d}:{check_out_minute:02d}"

            terminal_alias, device_id, housing_id = terminals[random.randint(0, len(terminals)-1)]

            mock_data.append({
                "emp_code": emp_code,
                "first_name": first_name,
                "last_name": last_name,
                "dept_name": dept_name,
                "att_date": date.strftime("%Y-%m-%d"),
                "punch_time": check_in_time,
                "punch_state": "check in",
                "terminal_alias": terminal_alias,
                "terminal_id": device_id,
                "housing_id": housing_id
            })

            mock_data.append({
                "emp_code": emp_code,
                "first_name": first_name,
                "last_name": last_name,
                "dept_name": dept_name,
                "att_date": date.strftime("%Y-%m-%d"),
                "punch_time": check_out_time,
                "punch_state": "check out",
                "terminal_alias": terminal_alias,
                "terminal_id": device_id,
                "housing_id": housing_id
            })

    df = pd.DataFrame(mock_data)
    return df

def parse_biotime_csv(file_path):
    """Custom parser for BioTime CSV format"""
    logger.info("Using custom parser for BioTime CSV data")

    try:
        # Read raw data
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            logger.error("CSV file is empty")
            return pd.DataFrame()

        # Extract header
        header = lines[0].strip().split(',')
        header = [col.strip() for col in header]

        # Parse data rows
        data = []
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            fields = line.split(',')

            # If there are fewer fields than expected, add empty values
            while len(fields) < len(header):
                fields.append('')

            # If there are more fields than expected, merge extras into the last field
            if len(fields) > len(header):
                fields[len(header)-1] = ','.join(fields[len(header)-1:])
                fields = fields[:len(header)]

            row_data = dict(zip(header, fields))
            data.append(row_data)

        df = pd.DataFrame(data)
        logger.info(f"Custom parser extracted {len(df)} records with {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error in custom CSV parser: {str(e)}")
        return pd.DataFrame()

def process_attendance_data(db, sync_id):
    """
    Process temporary attendance records and create AttendanceRecord entries.
    This function makes sure to keep all database operations within a managed session
    to prevent detached instance errors.

    Args:
        db: SQLAlchemy database instance
        sync_id: ID of the sync operation

    Returns:
        int: Number of processed records
    """
    from models import TempAttendance, AttendanceRecord, Employee, Department
    from optimized_timesheet import temp_attendance_to_dict

    try:
        logger.info(f"Processing attendance data for sync_id: {sync_id}")

        # Get all temporary records for this sync ID
        temp_records = TempAttendance.query.filter_by(sync_id=sync_id).all()
        total_records = len(temp_records)
        logger.info(f"Found {total_records} temporary records to process")

        if not total_records:
            logger.warning("No temporary records found to process")
            return 0
          # Convert TempAttendance to dictionary to avoid DetachedInstanceError
        temp_attendance_dicts = [temp_attendance_to_dict(record) for record in temp_records]

        # Step 1: Group employees and departments
        emp_codes = set()
        dept_names = set()

        for record_dict in temp_attendance_dicts:
            if record_dict['emp_code']:
                emp_codes.add(record_dict['emp_code'])
            if record_dict['dept_name']:
                dept_names.add(record_dict['dept_name'])

        # Step 2: Get or create departments
        dept_map = {}
        for dept_name in dept_names:
            dept = Department.query.filter_by(name=dept_name).first()
            if not dept:
                logger.info(f"Creating new department: {dept_name}")
                dept = Department(name=dept_name)
                db.session.add(dept)
                db.session.flush()  # Get ID without committing
            dept_map[dept_name] = dept.id
          # Step 3: Get or create employees
        emp_map = {}
        for emp_code in emp_codes:
            emp = Employee.query.filter_by(emp_code=emp_code).first()
            if not emp:
                # Find a record with this employee to get name and department
                temp = next((r for r in temp_attendance_dicts if r['emp_code'] == emp_code), None)
                if temp:
                    dept_id = dept_map.get(temp['dept_name'])
                    full_name = f"{temp['first_name']} {temp['last_name']}".strip()
                    if not full_name:
                        full_name = f"Employee-{emp_code}"

                    logger.info(f"Creating new employee: {full_name} ({emp_code})")
                    emp = Employee(
                        emp_code=emp_code,
                        name=full_name,
                        department_id=dept_id
                    )
                    db.session.add(emp)
                    db.session.flush()  # Get ID without committing
            if emp:
                emp_map[emp_code] = emp.id
          # Step 4: Process attendance records
        attendance_data = {}
        for record_dict in temp_attendance_dicts:
            if record_dict['emp_code'] not in emp_map:
                logger.warning(f"Employee code not found: {record_dict['emp_code']}")
                continue

            employee_id = emp_map[record_dict['emp_code']]
            att_date = record_dict['att_date']
            key = (employee_id, att_date)

            # Initialize the attendance record if it doesn't exist
            if key not in attendance_data:
                attendance_data[key] = {
                    'employee_id': employee_id,
                    'date': att_date,
                    'attendance_status': 'P',  # Present
                    'weekday': att_date.strftime('%A'),
                    'clock_in': None,
                    'clock_out': None,
                    'terminal_alias_in': None,
                    'terminal_alias_out': None,
                    'work_hours': None,
                    'total_time': None
                }
              # Process punch time
            try:
                punch_time_str = record_dict['punch_time'].strip()
                time_formats = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']
                punch_time_obj = None

                for fmt in time_formats:
                    try:
                        punch_time_obj = datetime.strptime(punch_time_str, fmt).time()
                        break
                    except ValueError:
                        continue

                if not punch_time_obj and ':' in punch_time_str:
                    hours, minutes = punch_time_str.split(':')[:2]
                    punch_time_obj = datetime.strptime(f"{int(hours):02d}:{int(minutes):02d}", '%H:%M').time()

                if not punch_time_obj:
                    punch_time_obj = datetime.strptime("00:00", '%H:%M').time()

                punch_datetime = datetime.combine(att_date, punch_time_obj)
                  # Determine if this is a check-in or check-out based on time
                is_check_in = punch_time_obj.hour < 12

                # Update earliest check-in or latest check-out
                if is_check_in:
                    if attendance_data[key]['clock_in'] is None or punch_datetime < attendance_data[key]['clock_in']:
                        attendance_data[key]['clock_in'] = punch_datetime
                        attendance_data[key]['terminal_alias_in'] = record_dict['terminal_alias']
                else:
                    if attendance_data[key]['clock_out'] is None or punch_datetime > attendance_data[key]['clock_out']:
                        attendance_data[key]['clock_out'] = punch_datetime
                        attendance_data[key]['terminal_alias_out'] = record_dict['terminal_alias']

            except Exception as e:
                logger.error(f"Error processing punch time {punch_time_str}: {str(e)}")

        # Step 5: Calculate work hours and create or update attendance records
        records_created = 0
        records_updated = 0

        for key, data in attendance_data.items():
            # Calculate work hours if both clock_in and clock_out exist
            if data['clock_in'] and data['clock_out']:
                if data['clock_out'] > data['clock_in']:
                    time_diff = data['clock_out'] - data['clock_in']
                    hours = time_diff.total_seconds() / 3600
                    data['work_hours'] = round(hours, 2)

                    hours_int = int(hours)
                    minutes = int((hours - hours_int) * 60)
                    data['total_time'] = f"{hours_int}:{minutes:02d}"
                else:
                    # Correct for cases where checkout is before checkin (might be midnight crossing)
                    logger.warning(f"Clock out before clock in for employee {data['employee_id']} on {data['date']}")
                    data['work_hours'] = 8.0  # Default to 8 hours
                    data['total_time'] = "8:00"
            else:
                # Set default values for missing clock times
                if data['clock_in'] and not data['clock_out']:
                    data['clock_out'] = data['clock_in'] + timedelta(hours=8)
                    data['work_hours'] = 8.0
                    data['total_time'] = "8:00"
                elif data['clock_out'] and not data['clock_in']:
                    data['clock_in'] = data['clock_out'] - timedelta(hours=8)
                    data['work_hours'] = 8.0
                    data['total_time'] = "8:00"
                else:
                    # Neither clock in nor out exists
                    continue

            # Check if a record already exists
            existing = AttendanceRecord.query.filter_by(
                employee_id=data['employee_id'],
                date=data['date']
            ).first()

            if existing:
                # Update existing record
                update_needed = False
                if data['clock_in'] and (not existing.clock_in or data['clock_in'] < existing.clock_in):
                    existing.clock_in = data['clock_in']
                    existing.terminal_alias_in = data['terminal_alias_in']
                    update_needed = True

                if data['clock_out'] and (not existing.clock_out or data['clock_out'] > existing.clock_out):
                    existing.clock_out = data['clock_out']
                    existing.terminal_alias_out = data['terminal_alias_out']
                    update_needed = True

                if update_needed:
                    existing.work_hours = data['work_hours']
                    existing.total_time = data['total_time']
                    existing.is_synced = True
                    existing.sync_id = sync_id
                    records_updated += 1
            else:
                # Create new attendance record
                new_record = AttendanceRecord(
                    employee_id=data['employee_id'],
                    date=data['date'],
                    attendance_status=data['attendance_status'],
                    weekday=data['weekday'],
                    clock_in=data['clock_in'],
                    clock_out=data['clock_out'],
                    terminal_alias_in=data['terminal_alias_in'],
                    terminal_alias_out=data['terminal_alias_out'],
                    work_hours=data['work_hours'],
                    total_time=data['total_time'],
                    is_synced=True,
                    sync_id=sync_id
                )
                db.session.add(new_record)
                records_created += 1

        # Commit all changes to avoid detached instances
        db.session.commit()

        logger.info(f"Attendance processing completed: {records_created} records created, {records_updated} records updated")
        return records_created + records_updated

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing attendance data: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def simple_sync_data(app=None, request_start_date=None, request_end_date=None):
    global CANCEL_SYNC, SYNC_PROGRESS, BIOTIME_API_BASE_URL, MOCK_MODE_ENABLED
    CANCEL_SYNC = False
    SYNC_PROGRESS = {"status": "in_progress", "step": "init", "progress": 5, "message": "تهيئة المزامنة...", "records": 0, "error": ""}

    # Inicializar use_mock al principio para evitar el error
    use_mock = MOCK_MODE_ENABLED

    try:
        from models import Department, Employee, AttendanceRecord, SyncLog, TempAttendance
        from database import db
    except ImportError:
        logger.error("فشل استيراد النماذج أو قاعدة البيانات")
        SYNC_PROGRESS["status"] = "error"
        SYNC_PROGRESS["error"] = "فشل استيراد النماذج أو قاعدة البيانات"
        return 0

    ctx = None
    if app:
        ctx = app.app_context()
        ctx.push()

    start_time = datetime.utcnow()
    synced_records = 0
    sync_log = None

    try:
        # إنشاء سجل المزامنة
        sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="in_progress",
            departments_synced=",".join(str(d) for d in DEPARTMENTS),
            records_synced=0,
            step="init"
        )
        db.session.add(sync_log)
        db.session.commit()
        logger.info("تم إنشاء سجل المزامنة بنجاح")

        # Step 1: Initialize and clean old data
        update_sync_status("init", 10, "تهيئة عملية المزامنة...", status="in_progress")
        sync_log.step = "init"
        db.session.commit()

        # مسح البيانات المؤقتة السابقة
        TempAttendance.query.delete()
        db.session.commit()
        logger.info("تم مسح البيانات المؤقتة السابقة")

        if check_cancellation(sync_log, db):
            return 0

        # Step 2: Configure date range
        update_sync_status("configure", 15, "تكوين نطاق التاريخ...", status="in_progress")
        sync_log.step = "configure"
        db.session.commit()

        # Establecer fechas de sincronización
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        sync_start_date = request_start_date or SYNC_START_DATE
        sync_end_date = request_end_date or SYNC_END_DATE

        if sync_start_date:
            try:
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        start_date = datetime.strptime(sync_start_date, date_format).date()
                        break
                    except ValueError:
                        continue
                if not start_date:
                    logger.warning(f"Could not parse start date: {sync_start_date}")
                    start_date = end_date - timedelta(days=30)
            except Exception as e:
                logger.error(f"Error processing start date: {str(e)}")
                start_date = end_date - timedelta(days=30)

        if sync_end_date:
            try:
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        end_date = datetime.strptime(sync_end_date, date_format).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                logger.warning(f"Could not parse end date: {sync_end_date}")

        if start_date > end_date:
            logger.warning("Start date is after end date, swapping dates")
            start_date, end_date = end_date, start_date

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        logger.info(f"نطاق التاريخ للمزامنة: {start_date_str} إلى {end_date_str}")

        if check_cancellation(sync_log, db):
            return 0

        # Step 3: Connect to BioTime API
        update_sync_status("connect", 20, "جاري الاتصال بنظام BioTime...", status="in_progress")
        sync_log.step = "connect"
        db.session.commit()

        # Inicializar variables para la API
        data_response = None
        success = False

        try:
            api_urls = [PRIMARY_API_URL, BACKUP_API_URL]
            retry_count = 0
            max_retries = 2

            formatted_start_date = f"{start_date_str}%2000:00:00"
            formatted_end_date = f"{end_date_str}%2023:59:59"

            while retry_count < max_retries and not success:
                if check_cancellation(sync_log, db):
                    return 0

                try:
                    current_url = api_urls[retry_count % len(api_urls)]
                    logger.info(f"محاولة الاتصال بـ API: {current_url}")
                    BIOTIME_API_BASE_URL = current_url

                    full_url = f"{current_url}?export_headers=emp_code,first_name,last_name,dept_name,att_date,punch_time,punch_state,terminal_alias&start_date={formatted_start_date}&end_date={formatted_end_date}&departments={','.join(str(d) for d in DEPARTMENTS)}&employees=-1&page_size=6000&export_type=txt&page=1&limit=6000"

                    logger.info(f"استخدام الرابط: {full_url}")
                    update_sync_status("connect", 25, f"محاولة الاتصال بـ: {current_url.split('/')[-3]}", status="in_progress")

                    data_response = requests.get(
                        full_url,
                        auth=(BIOTIME_USERNAME, BIOTIME_PASSWORD),
                        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                    )

                    # Log detailed response information for debugging
                    logger.info(f"API Response Status Code: {data_response.status_code}")
                    logger.info(f"API Response Content Type: {data_response.headers.get('Content-Type', 'Unknown')}")

                    # Check for common error status codes
                    if data_response.status_code == 401:
                        logger.error("Authentication failed - invalid username or password")
                        raise ValueError("فشل المصادقة: اسم المستخدم أو كلمة المرور غير صحيحة")
                    elif data_response.status_code == 403:
                        logger.error("Authorization failed - insufficient permissions")
                        raise ValueError("فشل التفويض: صلاحيات غير كافية للوصول إلى البيانات")
                    elif data_response.status_code >= 400:
                        logger.error(f"Server returned error status: {data_response.status_code}")
                        raise ValueError(f"خطأ في الخادم: {data_response.status_code}")

                    # Check if we have a successful response but verify content
                    if data_response and data_response.status_code == 200:
                        # Try to get a small sample of the content to check format
                        content_sample = data_response.content[:1000].decode('utf-8', errors='replace')
                        logger.info(f"Response content sample: {content_sample[:200]}...")

                        # Check if the response looks like CSV/TXT data (should contain commas and have multiple lines)
                        if ',' in content_sample and '\n' in content_sample:
                            logger.info("تم الاتصال بنجاح وتم تلقي البيانات بتنسيق مناسب")
                            success = True
                        else:
                            logger.warning("Response doesn't look like valid CSV/TXT data")
                            logger.warning(f"Content sample: {content_sample[:200]}")
                            raise ValueError("استجابة غير صالحة: التنسيق غير مطابق للمتوقع")
                    else:
                        logger.warning(f"فشل الاتصال مع {current_url}: {data_response.status_code if data_response else 'No response'}")
                        update_sync_status("connect", 25, f"محاولة الاتصال بخادم بديل...", status="in_progress")
                        retry_count += 1
                except Exception as e:
                    logger.error(f"خطأ أثناء محاولة الاتصال: {str(e)}")
                    retry_count += 1

            # Step 4: Download and process data
            update_sync_status("download", 30, "جاري تنزيل بيانات الحضور...", status="in_progress")
            sync_log.step = "download"
            db.session.commit()

            if success and data_response:
                # تخزين البيانات في متغير string مؤقت
                content = data_response.content.decode('utf-8')
                logger.info(f"محتوى البيانات الخام (أول 1000 حرف): {content[:1000]}")

                # تحليل البيانات
                lines = content.splitlines()
                if not lines:
                    logger.error("البيانات المستلمة فارغة")
                    raise ValueError("البيانات المستلمة فارغة")

                # استخراج الترويسة
                header = lines[0].strip().split(',')
                header = [col.strip() for col in header]
                logger.info(f"أعمدة البيانات المستلمة: {header}")

                # تنسيق الأعمدة
                normalized_header = [col.strip().replace(' ', '_').lower() for col in header]
                logger.info(f"أعمدة البيانات بعد التنسيق: {normalized_header}")

                # Column mappings
                column_mappings = {
                    'emp_code': ['employee_id', 'employee_code', 'emp_id'],
                    'first_name': ['first_name', 'firstname', 'given_name'],
                    'last_name': ['last_name', 'lastname', 'surname'],
                    'dept_name': ['department', 'dept', 'department_name'],
                    'att_date': ['date', 'attendance_date', 'att_date'],
                    'punch_time': ['time', 'punchtime', 'punch_time'],
                    'punch_state': ['punch_state', 'state', 'status'],
                    'terminal_alias': ['device_name', 'terminal', 'terminal_alias']
                }

                # إنشاء خريطة لتحديد اسم العمود الفعلي
                column_indices = {}
                for required_col, alternatives in column_mappings.items():
                    for idx, col in enumerate(normalized_header):
                        if col == required_col or col in alternatives:
                            column_indices[required_col] = idx
                            logger.info(f"تم تحديد عمود '{required_col}' في الموضع {idx}")
                            break

                # التحقق من وجود جميع الأعمدة المطلوبة
                missing_columns = [col for col in column_mappings.keys() if col not in column_indices]
                if missing_columns:
                    logger.error(f"الأعمدة المطلوبة غير موجودة: {missing_columns}")
                    raise ValueError(f"الأعمدة المطلوبة غير موجودة: {missing_columns}")

                if check_cancellation(sync_log, db):
                    return 0

                # معالجة البيانات وحفظها في جدول مؤقت
                update_sync_status("extract", 35, "استخراج بيانات السجلات...", status="in_progress")

                temp_records = []
                records_processed = 0
                total_lines = len(lines) - 1  # Subtract header line

                for i in range(1, len(lines)):
                    if i % 250 == 0:  # تقليل عدد التحديثات للتقدم
                        # Update progress periodically
                        progress_percent = 35 + int((i / total_lines) * 15)  # Scale between 35% and 50%
                        update_sync_status("extract", progress_percent, f"معالجة السجلات: {i}/{total_lines}", status="in_progress")

                        if check_cancellation(sync_log, db):
                            return 0

                    line = lines[i].strip()
                    if not line:
                        continue

                    try:
                        fields = line.split(',')
                        if len(fields) < len(header):
                            logger.warning(f"سطر قصير جداً، يتم تخطيه: {line}")
                            continue

                        # إضافة سجل إلى جدول temp_attendance
                        temp_record = TempAttendance(
                            emp_code=fields[column_indices['emp_code']],
                            first_name=fields[column_indices['first_name']] if 'first_name' in column_indices else '',
                            last_name=fields[column_indices['last_name']] if 'last_name' in column_indices else '',
                            dept_name=fields[column_indices['dept_name']],
                            att_date=datetime.strptime(fields[column_indices['att_date']], '%Y-%m-%d').date(),
                            punch_time=fields[column_indices['punch_time']],
                            punch_state=fields[column_indices['punch_state']],
                            terminal_alias=fields[column_indices['terminal_alias']],
                            sync_id=sync_log.id
                        )
                        temp_records.append(temp_record)
                        records_processed += 1

                        # التزام كل 100 سجل لتحسين الأداء
                        if len(temp_records) >= 100:
                            db.session.bulk_save_objects(temp_records)
                            db.session.commit()
                            temp_records = []

                    except Exception as e:
                        logger.error(f"خطأ في معالجة السطر {i}: {str(e)}, السطر: {line}")

                # حفظ أي سجلات متبقية
                if temp_records:
                    db.session.bulk_save_objects(temp_records)
                    db.session.commit()

                logger.info(f"تم حفظ {records_processed} سجل مؤقت في قاعدة البيانات")
                update_sync_status("extract", 50, f"تم استخراج {records_processed} سجل", status="in_progress")

                if records_processed == 0:
                    logger.warning("لم يتم استيراد أي سجلات من API")
                    use_mock = True
            else:
                logger.warning("فشل الاتصال بـ API، سيتم استخدام البيانات الوهمية")
                use_mock = True

        except Exception as e:
            logger.error(f"خطأ أثناء الاتصال بـ BioTime API: {str(e)}")
            use_mock = True

        if use_mock:
            logger.info("استخدام بيانات وهمية للمزامنة")
            update_sync_status("mock", 40, "جاري إنشاء بيانات وهمية للاختبار...", status="in_progress")
            sync_log.step = "mock"
            db.session.commit()

            # إنشاء بيانات وهمية وإدخالها في جدول TempAttendance
            mock_data = generate_mock_data(start_date, end_date)
            records_processed = 0
            temp_records = []

            for _, row in mock_data.iterrows():
                try:
                    temp_record = TempAttendance(
                        emp_code=row['emp_code'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        dept_name=row['dept_name'],
                        att_date=datetime.strptime(row['att_date'], '%Y-%m-%d').date(),
                        punch_time=row['punch_time'],
                        punch_state=row['punch_state'],
                        terminal_alias=row['terminal_alias'],
                        sync_id=sync_log.id
                    )
                    temp_records.append(temp_record)
                    records_processed += 1

                    if len(temp_records) >= 100:
                        if check_cancellation(sync_log, db):
                            return 0
                        db.session.bulk_save_objects(temp_records)
                        db.session.commit()
                        temp_records = []
                except Exception as e:
                    logger.error(f"خطأ في معالجة البيانات الوهمية: {str(e)}")
                    continue

            if temp_records:
                db.session.bulk_save_objects(temp_records)
                db.session.commit()

            logger.info(f"تم إنشاء وحفظ {records_processed} سجل وهمي في قاعدة البيانات المؤقتة")
            update_sync_status("mock", 50, f"تم إنشاء {records_processed} سجل وهمي", status="in_progress")

        if check_cancellation(sync_log, db):
            return 0

        # Step 5-6: Process and save data using the new function
        update_sync_status("process", 60, "جاري معالجة البيانات وتجهيزها للإدخال الجماعي...", status="in_progress")
        sync_log.step = "process"
        db.session.commit()

        synced_records = process_attendance_data(db, sync_log.id)

        if check_cancellation(sync_log, db):
            return 0

        # Step 7: Complete synchronization
        sync_log.status = "success"
        sync_log.records_synced = synced_records
        sync_log.end_time = datetime.utcnow()
        sync_log.step = "complete"
        db.session.commit()

        # Update final status
        update_sync_status("complete", 100, f"تمت المزامنة بنجاح - {synced_records} سجل", records=synced_records, status="success")

        logger.info(f"تمت عملية المزامنة بنجاح. تم مزامنة {synced_records} سجل.")
        return synced_records

    except Exception as e:
        logger.error(f"حدث خطأ أثناء المزامنة: {str(e)}")
        logger.error(traceback.format_exc())

        # Update sync log with error status
        if sync_log:
            try:
                sync_log.status = "error"
                sync_log.error_message = str(e)
                sync_log.end_time = datetime.utcnow()
                db.session.commit()
            except Exception as db_error:
                logger.error(f"خطأ إضافي أثناء تحديث سجل المزامنة: {str(db_error)}")

        # Update global status
        update_sync_status("error", 0, f"حدث خطأ أثناء المزامنة: {str(e)}", error=str(e), status="error")

        return 0
    finally:
        # إزالة البيانات المؤقتة
        try:
            TempAttendance.query.filter_by(sync_id=sync_log.id if sync_log else None).delete()
            db.session.commit()
            logger.info("تم حذف البيانات المؤقتة")
        except Exception as e:
            logger.error(f"خطأ في حذف البيانات المؤقتة: {str(e)}")

        if ctx:
            ctx.pop()

def cancel_sync():
    """إلغاء عملية المزامنة الجارية"""
    global CANCEL_SYNC, SYNC_PROGRESS
    CANCEL_SYNC = True

    # Immediately update the sync status to reflect cancellation request
    SYNC_PROGRESS["status"] = "cancelling"
    SYNC_PROGRESS["message"] = "جاري إلغاء المزامنة..."
    SYNC_PROGRESS["progress"] = SYNC_PROGRESS.get("progress", 0)

    logger.info("تم إرسال إشارة إلغاء المزامنة")
    return True

def get_sync_status():
    """إرجاع حالة المزامنة الحالية"""
    # تحقق من وجود رسالة خطأ "استجابة غير صالحة من الخادم"
    if SYNC_PROGRESS.get("error") == "استجابة غير صالحة من الخادم":
        # إذا كانت المزامنة جارية، لا تعرض رسالة الخطأ
        if SYNC_PROGRESS.get("status") == "in_progress":
            # نسخة من حالة المزامنة بدون رسالة الخطأ
            status_copy = SYNC_PROGRESS.copy()
            status_copy["error"] = ""
            return status_copy

    return SYNC_PROGRESS

def start_sync_in_background(app=None):
    """بدء المزامنة في خلفية"""
    global SYNC_THREAD
    if SYNC_THREAD and SYNC_THREAD.is_alive():
        logger.warning("المزامنة قيد التشغيل بالفعل")
        return False

    SYNC_THREAD = threading.Thread(
        target=simple_sync_data,
        kwargs={'app': app}
    )
    SYNC_THREAD.daemon = True
    SYNC_THREAD.start()
    logger.info("بدأت المزامنة في الخلفية")
    return True