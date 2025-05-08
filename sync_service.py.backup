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

        # Step 5: Process data
        update_sync_status("process", 60, "جاري معالجة البيانات...", status="in_progress")
        sync_log.step = "process"
        db.session.commit()
        
        # معالجة الأقسام
        for dept_record in db.session.query(TempAttendance.dept_name).distinct().all():
            dept_name = dept_record[0]
            if not dept_name:
                logger.warning("تم العثور على قسم بقيمة فارغة، يتم تخطيه")
                continue
            
            try:
                dept = Department.query.filter_by(name=dept_name).first()
                if not dept:
                    dept = Department(name=dept_name)
                    db.session.add(dept)
                    db.session.commit()
                    logger.info(f"تم إنشاء قسم جديد: {dept_name}")
            except Exception as e:
                logger.error(f"خطأ في معالجة القسم {dept_name}: {str(e)}")
                continue

        # Step 6: Save data
        update_sync_status("save", 70, "جاري حفظ البيانات في قاعدة البيانات...", status="in_progress")
        sync_log.step = "save"
        db.session.commit()

        # معالجة سجلات الحضور
        temp_records = TempAttendance.query.filter_by(sync_id=sync_log.id).all()
        total_records = len(temp_records)
        processed_count = 0
        
        for record in temp_records:
            processed_count += 1
            if processed_count % 200 == 0:  # تقليل عدد تحديثات حالة التقدم
                # Update progress every 50 records
                progress_percent = 70 + int((processed_count / total_records) * 20)  # Scale between 70% and 90%
                update_sync_status("save", progress_percent, f"حفظ السجلات: {processed_count}/{total_records}", status="in_progress")
                
                if check_cancellation(sync_log, db):
                    return 0
            
            try:
                dept = Department.query.filter_by(name=record.dept_name).first()
                if not dept:
                    logger.warning(f"لم يتم العثور على القسم {record.dept_name}")
                    continue

                employee = Employee.query.filter_by(emp_code=record.emp_code).first()
                if not employee:
                    employee = Employee(
                        emp_code=record.emp_code,
                        name=f"{record.first_name} {record.last_name}".strip(),
                        department_id=dept.id
                    )
                    db.session.add(employee)
                    db.session.commit()
                    logger.info(f"تم إنشاء موظف جديد: {record.emp_code}")

                # تحويل وقت البصمة إلى كائن datetime
                punch_time_obj = datetime.strptime(record.punch_time, '%H:%M').time()
                punch_datetime = datetime.combine(record.att_date, punch_time_obj)
                
                # تحديد نوع البصمة (دخول/خروج) بناءً على الوقت بدلاً من النص
                # نعتبر البصمات قبل الساعة 12 ظهراً هي بصمات دخول، وبعد الساعة 12 هي بصمات خروج
                is_check_in = punch_time_obj.hour < 12
                
                # البحث عن سجل حضور موجود لهذا الموظف في هذا اليوم
                attendance = AttendanceRecord.query.filter_by(
                    employee_id=employee.id,
                    date=record.att_date
                ).first()
                
                if not attendance:
                    # إنشاء سجل حضور جديد
                    attendance = AttendanceRecord(
                        employee_id=employee.id,
                        date=record.att_date,
                        attendance_status='P',
                        weekday=record.att_date.strftime('%A')
                    )
                    
                    # تعيين البصمة حسب النوع (دخول/خروج)
                    if is_check_in:
                        attendance.clock_in = punch_datetime
                        attendance.terminal_alias_in = record.terminal_alias
                    else:
                        attendance.clock_out = punch_datetime
                        attendance.terminal_alias_out = record.terminal_alias
                    
                    db.session.add(attendance)
                    synced_records += 1
                else:
                    # تحديث السجل الموجود
                    if is_check_in and attendance.clock_in is None:
                        attendance.clock_in = punch_datetime
                        attendance.terminal_alias_in = record.terminal_alias
                        synced_records += 1
                    elif not is_check_in and attendance.clock_out is None:
                        attendance.clock_out = punch_datetime
                        attendance.terminal_alias_out = record.terminal_alias
                        synced_records += 1
                
                # حساب إجمالي ساعات العمل إذا كان هناك بصمة دخول وخروج
                if attendance.clock_in and attendance.clock_out:
                    time_diff = attendance.clock_out - attendance.clock_in
                    hours = time_diff.total_seconds() / 3600
                    attendance.work_hours = round(hours, 2)
                    
                    hours_int = int(hours)
                    minutes = int((hours - hours_int) * 60)
                    attendance.total_time = f"{hours_int}:{minutes:02d}"
                
            except Exception as e:
                logger.error(f"خطأ في معالجة السجل: {str(e)}")
                continue

        try:
            db.session.commit()
            logger.info(f"تم حفظ {synced_records} سجل في قاعدة البيانات")
            update_sync_status("save", 90, f"تم حفظ {synced_records} سجل", status="in_progress")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"خطأ في حفظ البيانات في قاعدة البيانات: {str(e)}")
            update_sync_status("error", 0, error=str(e), status="error")
            return 0
            
        if check_cancellation(sync_log, db):
            return 0

        # Step 7: Complete synchronization
        sync_log.status = "success"
        sync_log.records_synced = synced_records
        sync_log.records_processed = records_processed
        sync_log.end_time = datetime.utcnow()
        sync_log.step = "complete"
        db.session.commit()
        
        # Update final status
        update_sync_status("complete", 100, f"تمت المزامنة بنجاح - {synced_records} سجل", records=synced_records, status="success")
        
        logger.info(f"تمت عملية المزامنة بنجاح. تم مزامنة {synced_records} من {records_processed} سجل.")
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