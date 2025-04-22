import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import tempfile
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_fixed

# إعداد التسجيل
logger = logging.getLogger(__name__)

# إعداد واجهة BioTime API
BIOTIME_API_BASE_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BIOTIME_USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
BIOTIME_PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")
DEPARTMENTS = [10]  # تحديث رقم القسم ليطابق الرابط الجديد

# إعدادات نطاق التاريخ للمزامنة
SYNC_START_DATE = os.environ.get("SYNC_START_DATE", "")
SYNC_END_DATE = os.environ.get("SYNC_END_DATE", "")

def sync_data(app=None):
    """
    مزامنة بيانات الحضور من BioTime API مع قاعدة البيانات.
    
    Args:
        app: مثيل تطبيق Flask (اختياري لإنشاء سياق التطبيق).
    
    Returns:
        None
    
    Raises:
        SQLAlchemyError: في حالة حدوث خطأ في قاعدة البيانات.
        RequestException: في حالة فشل الاتصال بـ API.
    """
    from app import db
    from models import Department, Employee, AttendanceRecord, SyncLog

    ctx = None
    if app:
        ctx = app.app_context()
        ctx.push()

    total_records = 0
    errors = []
    synced_depts = []
    sync_log = None
    start_time = datetime.utcnow()

    # استخدام نطاق التاريخ المُدخل من شاشة الإعدادات، وإلا استخدام آخر 30 يومًا
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # استخدام تاريخ البداية المُدخل إذا كان متاحًا
    if SYNC_START_DATE:
        try:
            # محاولة تحليل التاريخ بعدة تنسيقات شائعة
            for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    start_date = datetime.strptime(SYNC_START_DATE, date_format).date()
                    logger.info(f"تم تحليل تاريخ البداية بنجاح: {SYNC_START_DATE} -> {start_date} (تنسيق: {date_format})")
                    break
                except ValueError:
                    continue
            else:
                logger.warning(f"تعذر تحليل تاريخ البداية: {SYNC_START_DATE}. استخدام التاريخ الافتراضي: {start_date}")
        except Exception as e:
            logger.warning(f"خطأ في تحليل تاريخ البداية: {str(e)}. استخدام التاريخ الافتراضي: {start_date}")
    
    # استخدام تاريخ النهاية المُدخل إذا كان متاحًا
    if SYNC_END_DATE:
        try:
            # محاولة تحليل التاريخ بعدة تنسيقات شائعة
            for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    end_date = datetime.strptime(SYNC_END_DATE, date_format).date()
                    logger.info(f"تم تحليل تاريخ النهاية بنجاح: {SYNC_END_DATE} -> {end_date} (تنسيق: {date_format})")
                    break
                except ValueError:
                    continue
            else:
                logger.warning(f"تعذر تحليل تاريخ النهاية: {SYNC_END_DATE}. استخدام التاريخ الافتراضي: {end_date}")
        except Exception as e:
            logger.warning(f"خطأ في تحليل تاريخ النهاية: {str(e)}. استخدام التاريخ الافتراضي: {end_date}")
    
    # التأكد من أن تاريخ البداية أقدم من تاريخ النهاية
    if start_date > end_date:
        logger.warning(f"تاريخ البداية ({start_date}) لاحق لتاريخ النهاية ({end_date}). تبديل التواريخ.")
        start_date, end_date = end_date, start_date
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"بدء مزامنة بيانات BioTime من {start_date_str} إلى {end_date_str}")
    logger.info(f"التواريخ المُدخلة: البداية={SYNC_START_DATE or 'غير محدد'}, النهاية={SYNC_END_DATE or 'غير محدد'}")

    try:
        # إنشاء سجل مزامنة
        sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="in_progress",
            departments_synced=",".join(str(d) for d in DEPARTMENTS)
        )
        db.session.add(sync_log)
        db.session.commit()

        # جلب البيانات
        data = fetch_biotime_data(None, start_date_str, end_date_str)
        if data is not None and not data.empty:
            for dept_id in DEPARTMENTS:
                try:
                    records = process_department_data(dept_id, data)
                    total_records += records
                    if records > 0:
                        synced_depts.append(str(dept_id))
                        logger.info(f"تمت مزامنة القسم {dept_id} بنجاح - {records} سجل")
                except Exception as dept_e:
                    error_msg = f"خطأ في معالجة القسم {dept_id}: {str(dept_e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        else:
            error_msg = "لم يتم جلب بيانات من BioTime API."
            logger.warning(error_msg)
            errors.append(error_msg)

        # تحديث سجل المزامنة
        sync_log.status = "success" if not errors else "partial"
        sync_log.records_synced = total_records
        sync_log.departments_synced = ",".join(synced_depts) if synced_depts else ""
        sync_log.error_message = "\n".join(errors) if errors else None
        db.session.commit()

        logger.info(f"اكتملت المزامنة: {total_records} سجل، الوقت المستغرق: {datetime.utcnow() - start_time}")

    except Exception as e:
        logger.error(f"فشلت عملية المزامنة: {str(e)}", exc_info=True)
        if sync_log:
            sync_log.status = "error"
            sync_log.error_message = str(e)
            db.session.commit()

    finally:
        if ctx:
            ctx.pop()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_biotime_data(department_id, start_date, end_date):
    """
    جلب بيانات الحضور من BioTime API.
    
    Args:
        department_id: معرف القسم (غير مستخدم حاليًا).
        start_date: تاريخ البدء (بصيغة YYYY-MM-DD).
        end_date: تاريخ الانتهاء (بصيغة YYYY-MM-DD).
    
    Returns:
        DataFrame: بيانات الحضور أو DataFrame فارغ في حالة الخطأ.
    """
    start_datetime = f"{start_date} 00:00:00"
    end_datetime = f"{end_date} 23:59:59"
    departments_str = ",".join(str(d) for d in DEPARTMENTS)

    params = {
        "export_headers": "emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias",
        "start_date": start_datetime,
        "end_date": end_datetime,
        "departments": departments_str,
        "employees": -1,
        "page_size": 6000,
        "export_type": "txt",
        "page": 1,
        "limit": 6000
    }

    temp_filename = None
    try:
        if os.environ.get("DATABASE_URL", "").find("neon.tech") >= 0:
            logger.info("استخدام قاعدة بيانات Neon PostgreSQL. إنشاء بيانات اختبار.")
            return pd.DataFrame(columns=[
                'emp_code', 'first_name', 'dept_name', 'att_date',
                'punch_time', 'punch_state', 'terminal_alias'
            ])

        response = requests.get(
            BIOTIME_API_BASE_URL,
            params=params,
            auth=(BIOTIME_USERNAME, BIOTIME_PASSWORD),
            timeout=15,
            stream=True
        )
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='wb') as temp:
            temp.write(response.content)
            temp_filename = temp.name

        # قراءة البيانات على دفعات لتحسين إدارة الذاكرة
        data = pd.read_csv(temp_filename, sep='\t', encoding='utf-8', chunksize=1000)
        data = pd.concat(data)
        logger.debug(f"تم جلب {len(data)} سجل للقسم {department_id}")
        return data

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"خطأ HTTP في واجهة BioTime: {str(http_err)}")
        return pd.DataFrame(columns=[
            'emp_code', 'first_name', 'dept_name', 'att_date',
            'punch_time', 'punch_state', 'terminal_alias'
        ])
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"خطأ في الاتصال بـ BioTime: {str(conn_err)}")
        raise
    except Exception as e:
        logger.error(f"خطأ في جلب البيانات: {str(e)}")
        return pd.DataFrame(columns=[
            'emp_code', 'first_name', 'dept_name', 'att_date',
            'punch_time', 'punch_state', 'terminal_alias'
        ])
    finally:
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logger.error(f"خطأ في حذف الملف المؤقت: {str(e)}")

def process_department_data(department_id, data):
    """
    معالجة بيانات القسم من BioTime وتحديث قاعدة البيانات.
    
    Args:
        department_id: معرف القسم.
        data: DataFrame يحتوي على بيانات الحضور.
    
    Returns:
        int: عدد السجلات المعالجة.
    """
    from app import db
    from models import Department, Employee, AttendanceRecord

    try:
        dept_data = data[data['dept_name'].str.contains(f"Department {department_id}", na=False)] if 'dept_name' in data.columns else data
        if dept_data.empty:
            logger.warning(f"لا توجد بيانات متاحة للقسم {department_id}")
            return 0

        # التأكد من وجود القسم
        dept = Department.query.filter_by(dept_id=str(department_id)).first()
        if not dept:
            dept_name = dept_data['dept_name'].iloc[0] if 'dept_name' in dept_data.columns else f"Department {department_id}"
            dept = Department(dept_id=str(department_id), name=dept_name, active=True)
            db.session.add(dept)
            db.session.flush()

        # تخزين الموظفين مؤقتًا
        emp_codes = dept_data['emp_code'].unique()
        existing_employees = {e.emp_code: e for e in Employee.query.filter(Employee.emp_code.in_(emp_codes)).all()}
        new_employees = []
        attendance_records = []

        for _, row in dept_data.iterrows():
            try:
                emp_code = str(row['emp_code'])
                att_date = datetime.strptime(row['att_date'], '%Y-%m-%d').date() if 'att_date' in row else None
                if not att_date:
                    continue

                # الحصول على الموظف أو إنشاؤه
                employee = existing_employees.get(emp_code)
                if not employee:
                    employee = Employee(
                        emp_code=emp_code,
                        name=row.get('first_name', ''),
                        department_id=dept.id
                    )
                    new_employees.append(employee)
                    existing_employees[emp_code] = employee

                punch_state = row.get('punch_state', '').lower() if pd.notna(row.get('punch_state')) else ''
                punch_time = row.get('punch_time') if pd.notna(row.get('punch_time')) else None
                if not punch_time:
                    continue

                punch_datetime = datetime.strptime(f"{row['att_date']} {punch_time}", '%Y-%m-%d %H:%M:%S')
                clock_in = punch_datetime if 'in' in punch_state else None
                clock_out = punch_datetime if 'out' in punch_state else None

                # التحقق من وجود سجل حضور
                attendance = AttendanceRecord.query.filter_by(
                    employee_id=employee.id,
                    date=att_date
                ).first()

                if attendance:
                    if clock_in and (not attendance.clock_in or clock_in < attendance.clock_in):
                        attendance.clock_in = clock_in
                    if clock_out and (not attendance.clock_out or clock_out > attendance.clock_out):
                        attendance.clock_out = clock_out
                else:
                    attendance = AttendanceRecord(
                        employee_id=employee.id,
                        date=att_date,
                        weekday=att_date.strftime('%A'),
                        clock_in=clock_in,
                        clock_out=clock_out,
                        attendance_status='P' if clock_in or clock_out else 'A'
                    )
                    attendance_records.append(attendance)

            except Exception as e:
                logger.error(f"خطأ في معالجة السجل: {str(e)}")
                continue

        # حفظ الموظفين والسجلات دفعة واحدة
        db.session.bulk_save_objects(new_employees)
        db.session.bulk_save_objects(attendance_records)
        db.session.commit()
        logger.info(f"تمت معالجة {len(attendance_records)} سجل للقسم {department_id}")
        return len(attendance_records)

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"خطأ في قاعدة البيانات: {str(e)}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطأ في معالجة بيانات القسم: {str(e)}")
        raise

def process_uploaded_file(file_path):
    """
    معالجة ملف مرفوع يحتوي على بيانات الحضور.
    
    Args:
        file_path: مسار الملف المرفوع.
    
    Returns:
        int: عدد السجلات المعالجة.
    """
    from app import db
    from models import Department, Employee, AttendanceRecord, SyncLog

    try:
        # محاولة قراءة الملف بصيغ مختلفة
        try:
            data = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        except:
            try:
                data = pd.read_csv(file_path, encoding='utf-8')
            except:
                data = pd.read_excel(file_path)

        # Log the actual columns found in the file for debugging
        logger.info(f"الأعمدة الموجودة في الملف المرفوع: {list(data.columns)}")
        
        # تعيين الأعمدة بمرونة - مع المزيد من البدائل
        column_mapping = {
            'emp_code': ['emp_code', 'C. No.', 'employee_code', 'employee id', 'emp id', 'code', 'emp', 'id', 'رقم الموظف', 'الرقم', 'c.no', 'code', 'no', 'empcode', 'emp.code'],
            'att_date': ['att_date', 'date', 'Date', 'تاريخ', 'day', 'يوم', 'punch_date', 'التاريخ', 'att date', 'attdate', 'attendance date', 'التاريخ', 'record date', 'recorddate'],
            'first_name': ['first_name', 'name', 'Employee Name', 'اسم الموظف', 'الاسم', 'emp name', 'empname', 'full name', 'fullname', 'employee', 'first name'],
            'dept_name': ['dept_name', 'department', 'Department', 'القسم', 'اسم القسم', 'dept', 'department name', 'deptname'],
            'clock_in': ['clock_in', 'Clock In', 'time in', 'وقت الحضور', 'حضور', 'checkin', 'check in', 'punch_time_in', 'in', 'time-in', 'timein', 'in time'],
            'clock_out': ['clock_out', 'Clock Out', 'time out', 'وقت الانصراف', 'انصراف', 'checkout', 'check out', 'punch_time_out', 'out', 'time-out', 'timeout', 'out time']
        }

        # Add a case-insensitive search for columns
        for standard_col, possible_cols in column_mapping.items():
            # First try exact matches
            found = False
            for col in possible_cols:
                if col in data.columns:
                    data.rename(columns={col: standard_col}, inplace=True)
                    found = True
                    break
                    
            # If not found, try case-insensitive matches
            if not found:
                for col in data.columns:
                    for possible_col in possible_cols:
                        if col.lower() == possible_col.lower() or possible_col.lower() in col.lower():
                            data.rename(columns={col: standard_col}, inplace=True)
                            found = True
                            break
                    if found:
                        break
        
        # If still missing required columns, check if punch_time and punch_state can be used to create them
        if 'punch_time' in data.columns and 'att_date' not in data.columns and 'punch_state' in data.columns:
            try:
                # Try to extract date from punch_time if it contains date information
                data['att_date'] = pd.to_datetime(data['punch_time']).dt.date.astype(str)
                logger.info("تم استخراج تاريخ الحضور من عمود punch_time")
            except:
                logger.warning("فشل استخراج التاريخ من عمود punch_time")
                
        required_cols = ['emp_code', 'att_date']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"الملف يفتقد الأعمدة الضرورية: {missing_cols}")

        if data.empty:
            logger.warning("الملف المرفوع لا يحتوي على بيانات")
            return 0

        # إنشاء سجل مزامنة
        sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="in_progress",
            departments_synced="تحميل يدوي"
        )
        db.session.add(sync_log)
        db.session.commit()

        records = process_manual_upload_data(None, data)

        sync_log.status = "success"
        sync_log.records_synced = records
        sync_log.departments_synced = f"تحميل يدوي: {records} سجل"
        db.session.commit()
        logger.info(f"اكتملت معالجة الملف: {records} سجل")
        return records

    except Exception as e:
        logger.error(f"خطأ في معالجة الملف المرفوع: {str(e)}")
        if 'sync_log' in locals():
            sync_log.status = "error"
            sync_log.error_message = str(e)
            db.session.commit()
        return 0

def process_manual_upload_data(dept_id, data):
    """
    معالجة بيانات التحميل اليدوي لقسم معين.
    
    Args:
        dept_id: معرف القسم (None إذا لم يتم تحديده).
        data: DataFrame يحتوي على بيانات الحضور.
    
    Returns:
        int: عدد السجلات المعالجة.
    """
    from app import db
    from models import Department, Employee, AttendanceRecord

    try:
        # إعادة الاتصال بقاعدة البيانات
        db.session.rollback()
        db.engine.connect().close()

        # إنشاء قسم افتراضي إذا لم يتم تحديده
        if dept_id:
            dept = Department.query.filter_by(dept_id=str(dept_id)).first()
            if not dept:
                dept_name = f"Department {dept_id}"
                dept = Department(dept_id=str(dept_id), name=dept_name, active=True)
                db.session.add(dept)
                db.session.flush()
        else:
            dept = None

        emp_codes = data['emp_code'].astype(str).unique()
        # Fetch existing employees to avoid redundant queries
        existing_employees = {e.emp_code: e for e in Employee.query.filter(Employee.emp_code.in_(emp_codes)).all()}
        new_employees = []
        attendance_records = []

        for index, row in data.iterrows():
            try:
                emp_code = str(row['emp_code'])
                att_date = None
                if 'att_date' in row and pd.notna(row['att_date']):
                    try:
                        att_date = pd.to_datetime(row['att_date']).date()
                    except:
                        logger.warning(f"خطأ في تحليل التاريخ للموظف {emp_code}")
                        continue

                if not att_date:
                    logger.warning(f"تخطي السجل: لا يوجد تاريخ للموظف {emp_code}")
                    continue

                # الحصول على الموظف أو إنشاؤه
                employee = existing_employees.get(emp_code)
                if not employee:
                    employee = Employee(
                        emp_code=emp_code,
                        name=row.get('first_name', f"Employee {emp_code}"),
                        department_id=dept.id if dept else None
                    )
                    new_employees.append(employee)
                    existing_employees[emp_code] = employee

                # معالجة أوقات الدخول والخروج
                clock_in = pd.to_datetime(row.get('clock_in')).to_pydatetime() if 'clock_in' in row and pd.notna(row['clock_in']) else None
                clock_out = pd.to_datetime(row.get('clock_out')).to_pydatetime() if 'clock_out' in row and pd.notna(row['clock_out']) else None

                # التحقق من وجود سجل
                attendance = AttendanceRecord.query.filter_by(
                    employee_id=employee.id,
                    date=att_date
                ).first()

                if attendance:
                    attendance.clock_in = clock_in or attendance.clock_in
                    attendance.clock_out = clock_out or attendance.clock_out
                    attendance.attendance_status = 'P' if clock_in or clock_out else 'A'
                    attendance.updated_at = datetime.utcnow()
                else:
                    attendance = AttendanceRecord(
                        employee_id=employee.id,
                        date=att_date,
                        weekday=att_date.strftime('%A'),
                        clock_in=clock_in,
                        clock_out=clock_out,
                        attendance_status='P' if clock_in or clock_out else 'A'
                    )
                    attendance_records.append(attendance)

            except Exception as e:
                logger.error(f"خطأ في معالجة السجل {index}: {str(e)}")
                continue

        # حفظ البيانات دفعة واحدة
        db.session.bulk_save_objects(new_employees)
        db.session.bulk_save_objects(attendance_records)
        db.session.commit()
        return len(attendance_records)

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"خطأ في قاعدة البيانات: {str(e)}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطأ في معالجة البيانات: {str(e)}")
        raise