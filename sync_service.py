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

# إعداد التسجيل
logger = logging.getLogger(__name__)

# إعداد واجهة BioTime API
PRIMARY_API_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BACKUP_API_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/" 
BIOTIME_API_BASE_URL = PRIMARY_API_URL  # Default to primary URL
BIOTIME_USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
BIOTIME_PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")
DEPARTMENTS = [10]  # تحديث رقم القسم ليطابق الرابط الجديد

# إعدادات نطاق التاريخ للمزامنة
SYNC_START_DATE = os.environ.get("SYNC_START_DATE", "")
SYNC_END_DATE = os.environ.get("SYNC_END_DATE", "")

# Connection timeout settings
CONNECT_TIMEOUT = 30  # Timeout for establishing connection
READ_TIMEOUT = 180    # Timeout for reading response

# متغير عالمي للتحكم في حالة المزامنة - لن نستخدم المتغير من app.py بعد الآن
CANCEL_SYNC = False
SYNC_THREAD = None
SYNC_PROGRESS = {"status": "none", "step": "", "progress": 0, "message": "", "records": 0, "error": ""}

def calculate_work_hours(clock_in, clock_out, standard_hours, is_friday=False, is_thursday=False, friday_hours=8):
    """
    حساب ساعات العمل والوقت الإضافي بناءً على وقت الدخول والخروج وساعات العمل القياسية
    
    Args:
        clock_in: وقت تسجيل الدخول (datetime)
        clock_out: وقت تسجيل الخروج (datetime)
        standard_hours: ساعات العمل القياسية للموظف (float)
        is_friday: هل هذا يوم الجمعة؟ (boolean)
        is_thursday: هل هذا يوم الخميس؟ (boolean)
        friday_hours: عدد ساعات يوم الجمعة الافتراضية للموظفين غير المداومين (int)
        
    Returns:
        tuple: (ساعات العمل الفعلية، ساعات العمل الإضافي)
    """
    # إذا كان أحد الأوقات غير موجود، فلا يمكن حساب ساعات العمل
    if not clock_in or not clock_out:
        # للموظفين غير المداومين يوم الجمعة، نعطي ساعات عمل افتراضية
        if is_friday:
            return friday_hours, 0
        return 0, 0
        
    # حساب الفرق بالساعات
    time_diff = clock_out - clock_in
    total_hours = time_diff.total_seconds() / 3600  # تحويل الثواني إلى ساعات
    
    # لا نقبل قيم سالبة أو قيم كبيرة جداً (أكثر من 24 ساعة)
    if total_hours <= 0 or total_hours > 24:
        if is_friday:
            return friday_hours, 0
        return 0, 0
    
    # تقريب إجمالي الساعات إلى أقرب ربع ساعة
    total_hours = round(total_hours * 4) / 4  # تقريب لأقرب 0.25
    
    # في يوم الجمعة للمداومين، نعتبر كل الساعات إضافية
    if is_friday:
        # للموظفين المداومين في يوم الجمعة (لديهم بصمات)
        # جميع الساعات تحتسب كساعات إضافية
        return 0, total_hours
    
    # تعامل خاص مع يوم الخميس - 5.5 ساعات تحتسب كيوم كامل (8 ساعات)
    if is_thursday:
        standard_thursday_hours = 5.5  # ساعات الدوام المعيارية يوم الخميس
        
        # تطبيق النسبة والتناسب لحساب ساعات العمل في يوم الخميس
        # إذا عمل الموظف ساعات أقل من المعيار (5.5)، نطبق النسبة والتناسب
        if total_hours < standard_thursday_hours:
            # نسبة الساعات التي عملها الموظف إلى ساعات الدوام المعيارية
            ratio = total_hours / standard_thursday_hours
            # حساب ساعات العمل الفعلية بناءً على النسبة (من 8 ساعات)
            actual_work_hours = ratio * 8
            return actual_work_hours, 0
        else:
            # إذا عمل الموظف 5.5 ساعات أو أكثر، يحتسب له 8 ساعات كاملة
            # أي ساعات فوق 5.5 تعتبر وقت إضافي
            overtime = max(0, total_hours - standard_thursday_hours)
            return 8, overtime
    
    # للأيام العادية (غير الخميس والجمعة)
    standard_day_hours = 8.5  # ساعات الدوام المعيارية في الأيام العادية
    max_counted_hours = 8.0    # الحد الأقصى للساعات المحتسبة
    
    # إذا عمل أقل من المعيار، نطبق النسبة والتناسب
    if total_hours < standard_day_hours:
        # نسبة الساعات التي عملها الموظف إلى ساعات الدوام المعيارية
        ratio = total_hours / standard_day_hours
        # حساب ساعات العمل الفعلية بناءً على النسبة (من 8 ساعات)
        actual_work_hours = ratio * max_counted_hours
        return actual_work_hours, 0
    else:
        # إذا عمل المعيار كاملاً (8.5) أو أكثر، يحتسب له 8 ساعات
        # وأي ساعات إضافية فوق المعيار (8.5) تحسب كوقت إضافي
        overtime = max(0, total_hours - standard_day_hours)
        return max_counted_hours, overtime

def update_sync_status(step, progress, message=None, error=None, records=0, status=None):
    """تحديث حالة المزامنة العالمية"""
    global SYNC_PROGRESS
    SYNC_PROGRESS["step"] = step
    SYNC_PROGRESS["progress"] = progress
    if message:
        SYNC_PROGRESS["message"] = message
    if error:
        SYNC_PROGRESS["error"] = error
    if records > 0:
        SYNC_PROGRESS["records"] = records
    if status:
        SYNC_PROGRESS["status"] = status
    
    logger.debug(f"تحديث حالة المزامنة: {step}, {progress}%, {message}, حالة: {status or SYNC_PROGRESS['status']}")

def check_cancellation(sync_log=None, db=None):
    """التحقق من طلب إلغاء المزامنة"""
    global CANCEL_SYNC
    
    if CANCEL_SYNC:
        logger.warning("تم اكتشاف طلب إلغاء المزامنة")
        SYNC_PROGRESS["status"] = "cancelled"
        
        if sync_log and db:
            try:
                sync_log.status = "cancelled"
                sync_log.error_message = "تم إلغاء المزامنة بواسطة المستخدم"
                sync_log.end_time = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                logger.error(f"خطأ أثناء تحديث سجل المزامنة بعد الإلغاء: {str(e)}")
                
        return True
    return False

def reset_sync_state():
    """إعادة تعيين متغيرات حالة المزامنة العالمية"""
    global CANCEL_SYNC, SYNC_THREAD, SYNC_PROGRESS
    CANCEL_SYNC = False
    SYNC_THREAD = None
    SYNC_PROGRESS = {"status": "none", "step": "", "progress": 0, "message": "", "records": 0, "error": ""}

def simple_sync_data(app=None):
    """
    وظيفة مبسطة لمزامنة بيانات الحضور من BioTime API. تستخدم طريقة مباشرة بخطوات واضحة:
    1. جلب البيانات من API
    2. حفظها في ملف محلي
    3. معالجة البيانات حسب الاحتياجات
    4. حفظ البيانات في قاعدة البيانات
    
    Args:
        app: مثيل تطبيق Flask (اختياري لإنشاء سياق التطبيق)
    
    Returns:
        int: عدد السجلات التي تمت مزامنتها بنجاح
    """
    # إعادة تعيين حالة المزامنة
    global CANCEL_SYNC, SYNC_PROGRESS, BIOTIME_API_BASE_URL
    CANCEL_SYNC = False
    SYNC_PROGRESS = {"status": "in_progress", "step": "connect", "progress": 10, "message": "بدء المزامنة...", "records": 0, "error": ""}
    
    # استيراد المكتبات المطلوبة
    try:
        from models import Department, Employee, AttendanceRecord, SyncLog
        from database import db
    except ImportError:
        logger.error("فشل استيراد النماذج أو قاعدة البيانات - التأكد من تشغيل التطبيق في إطار سياق Flask")
        SYNC_PROGRESS["status"] = "error"
        SYNC_PROGRESS["error"] = "فشل استيراد النماذج أو قاعدة البيانات"
        return 0
    
    import csv
    
    # دفع سياق التطبيق إذا تم تمريره
    ctx = None
    if app:
        ctx = app.app_context()
        ctx.push()
    
    start_time = datetime.utcnow()
    synced_records = 0
    sync_log = None
    temp_file = "attendance_data_tmp.csv"
    
    try:
        # 1. إعداد سجل المزامنة
        try:
            sync_log = SyncLog(
                sync_time=datetime.utcnow(),
                status="in_progress",
                departments_synced=",".join(str(d) for d in DEPARTMENTS),
                records_synced=0,
                step="connect"
            )
            db.session.add(sync_log)
            db.session.commit()
            logger.info("تم إنشاء سجل المزامنة بنجاح")
        except Exception as e:
            logger.error(f"خطأ في إنشاء سجل المزامنة: {str(e)}")
            SYNC_PROGRESS["status"] = "error"
            SYNC_PROGRESS["error"] = f"خطأ في إنشاء سجل المزامنة: {str(e)}"
            return 0

        # التحقق من الإلغاء
        if check_cancellation(sync_log, db):
            return 0
            
        # 2. تحديد نطاق التاريخ
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        if SYNC_START_DATE:
            try:
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        start_date = datetime.strptime(SYNC_START_DATE, date_format).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
                
        if SYNC_END_DATE:
            try:
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        end_date = datetime.strptime(SYNC_END_DATE, date_format).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
                
        if start_date > end_date:
            start_date, end_date = end_date, start_date
            
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"نطاق التاريخ للمزامنة: {start_date_str} إلى {end_date_str}")
        
        # التحقق من الإلغاء
        if check_cancellation(sync_log, db):
            return 0
            
        # 3. تكوين عنوان URL وإعداد الاتصال
        update_sync_status("connect", 20, "الاتصال بنظام البصمة وتحميل البيانات...")

        departments_str = ",".join(str(d) for d in DEPARTMENTS)
        start_datetime = f"{start_date_str} 00:00:00"
        end_datetime = f"{end_date_str} 23:59:59"
        
        # Store query parameters for reuse with different URLs
        query_params = f"?export_headers=emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias&start_date={start_datetime}&end_date={end_datetime}&departments={departments_str}&employees=-1&page_size=6000&export_type=txt&page=1&limit=6000"
        
        # First try with primary URL
        api_url = f"{PRIMARY_API_URL}{query_params}"
        logger.info(f"محاولة الاتصال بالخادم الرئيسي: {api_url}")
        
        # 4. إرسال الطلب للحصول على البيانات
        response = None
        try:
            # Try the primary API URL first
            response = requests.get(
                api_url,
                auth=(BIOTIME_USERNAME, BIOTIME_PASSWORD),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )
            
            if response.ok:
                logger.info("تم الاتصال بالخادم الرئيسي بنجاح")
                BIOTIME_API_BASE_URL = PRIMARY_API_URL  # Keep using primary URL
            else:
                # Primary server returned an error response
                logger.warning(f"فشل الاتصال بالخادم الرئيسي (رمز الخطأ: {response.status_code}). جاري المحاولة بالخادم البديل.")
                response = None  # Reset response to trigger backup server
                
        except requests.RequestException as e:
            # Connection to primary server failed
            logger.warning(f"فشل الاتصال بالخادم الرئيسي: {str(e)}. جاري المحاولة بالخادم البديل.")
            response = None  # Set response to None to try backup
        
        # If primary server failed, try the backup URL
        if response is None or not response.ok:
            # Try with backup URL
            backup_api_url = f"{BACKUP_API_URL}{query_params}"
            logger.info(f"محاولة الاتصال بالخادم البديل: {backup_api_url}")
            
            try:
                response = requests.get(
                    backup_api_url,
                    auth=(BIOTIME_USERNAME, BIOTIME_PASSWORD),
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                )
                
                if response.ok:
                    logger.info("تم الاتصال بالخادم البديل بنجاح")
                    # Update the base URL to use backup for future requests
                    BIOTIME_API_BASE_URL = BACKUP_API_URL
                else:
                    error_msg = f"فشل الاتصال بالخادم البديل أيضا: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    sync_log.status = "error"
                    sync_log.error_message = error_msg
                    db.session.commit()
                    SYNC_PROGRESS["status"] = "error"
                    SYNC_PROGRESS["error"] = error_msg
                    return 0
                    
            except requests.RequestException as backup_e:
                error_msg = f"فشل الاتصال بالخادم البديل أيضا: {str(backup_e)}"
                logger.error(error_msg)
                sync_log.status = "error" 
                sync_log.error_message = error_msg
                db.session.commit()
                SYNC_PROGRESS["status"] = "error"
                SYNC_PROGRESS["error"] = error_msg
                return 0
                
        # If still no valid response after trying both servers
        if not response or not response.ok:
            error_msg = "فشل الاتصال بخوادم النظام"
            logger.error(error_msg)
            sync_log.status = "error"
            sync_log.error_message = error_msg
            db.session.commit()
            SYNC_PROGRESS["status"] = "error"
            SYNC_PROGRESS["error"] = error_msg
            return 0
        
        # التحقق من الإلغاء
        if check_cancellation(sync_log, db):
            return 0

        # 5. حفظ البيانات إلى ملف مؤقت
        update_sync_status("download", 40, "تم تحميل البيانات، جاري المعالجة...")
        
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(response.text)
                
            logger.info(f"تم حفظ البيانات إلى ملف مؤقت: {temp_file}")
            
            # تحديث سجل المزامنة
            sync_log.step = "process"
            db.session.commit()
        except Exception as e:
            error_msg = f"خطأ في حفظ البيانات إلى ملف مؤقت: {str(e)}"
            logger.error(error_msg)
            sync_log.status = "error"
            sync_log.error_message = error_msg
            db.session.commit()
            SYNC_PROGRESS["status"] = "error"
            SYNC_PROGRESS["error"] = error_msg
            return 0
        
        # التحقق من الإلغاء
        if check_cancellation(sync_log, db):
            return 0
            
        # 6. معالجة البيانات
        update_sync_status("process", 60, "جاري معالجة البيانات...")
        
        try:
            # تحديد نوع الملف وقراءة البيانات
            delimiter = '\t'  # افتراضي لملفات BioTime
            with open(temp_file, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if ',' in first_line and ',' in first_line.split('\t')[0]:
                    delimiter = ','
            
            # قراءة البيانات باستخدام pandas - أكثر موثوقية من القراءة اليدوية
            try:
                df = pd.read_csv(temp_file, delimiter=delimiter, encoding='utf-8')
                logger.info(f"تم قراءة {len(df)} سجل بنجاح باستخدام pandas")
            except Exception as pandas_error:
                logger.warning(f"فشلت قراءة الملف باستخدام pandas: {str(pandas_error)}")
                
                # محاولة بديلة باستخدام القراءة اليدوية
                rows = []
                headers = []
                
                with open(temp_file, "r", encoding="utf-8") as f:
                    if delimiter == ',':
                        # CSV
                        csv_reader = csv.reader(f, delimiter=delimiter)
                        headers = next(csv_reader)  # قراءة العناوين
                        rows = list(csv_reader)  # قراءة البيانات
                    else:
                        # ملف مفصول بتبويب
                        lines = f.readlines()
                        if lines:
                            headers = [h.strip() for h in lines[0].split(delimiter)]
                            for line in lines[1:]:
                                rows.append([cell.strip() for cell in line.split(delimiter)])
                
                # تحويل البيانات إلى DataFrame
                if headers and rows:
                    df = pd.DataFrame(rows, columns=headers)
                    logger.info(f"تم قراءة {len(df)} سجل بنجاح باستخدام القراءة اليدوية")
                else:
                    raise ValueError("فشلت قراءة البيانات من الملف المؤقت")
            
            # تنسيق أسماء الأعمدة
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
            
            # محاولة توحيد أسماء الأعمدة المتوقعة
            column_mapping = {
                'employee_id': 'emp_code',
                'first_name': 'first_name',
                'name': 'first_name',
                'full_name': 'first_name',
                'department': 'dept_name',
                'dept_name': 'dept_name',
                'date': 'att_date',
                'att_date': 'att_date',
                'time': 'punch_time',
                'punch_time': 'punch_time',
                'punch_state': 'punch_state',
                'state': 'punch_state',
                'terminal_alias': 'terminal_alias',
                'device_name': 'terminal_alias'
            }
            
            # تطبيق التعيين على الأعمدة المتاحة
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and old_col != new_col:
                    df[new_col] = df[old_col]
            
            # التحقق من وجود الأعمدة الضرورية
            required_columns = ['emp_code', 'att_date', 'punch_time', 'punch_state']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                error_msg = f"الأعمدة المطلوبة مفقودة في البيانات: {', '.join(missing_columns)}"
                logger.error(error_msg)
                sync_log.status = "error"
                sync_log.error_message = error_msg
                db.session.commit()
                SYNC_PROGRESS["status"] = "error"
                SYNC_PROGRESS["error"] = error_msg
                return 0
            
            logger.info(f"الأعمدة في البيانات: {', '.join(df.columns.tolist())}")
            
            # تصفية البيانات للقسم المطلوب (HOUSING/10)
            housing_df = df[df['dept_name'].str.contains('HOUSING', case=False, na=False)]
            
            if len(housing_df) == 0:
                error_msg = "لم يتم العثور على بيانات للقسم HOUSING"
                logger.error(error_msg)
                sync_log.status = "error" 
                sync_log.error_message = error_msg
                db.session.commit()
                SYNC_PROGRESS["status"] = "error"
                SYNC_PROGRESS["error"] = error_msg
                return 0
                
            logger.info(f"تم العثور على {len(housing_df)} سجل للقسم HOUSING")
            
            # تحويل جميع رموز الموظفين إلى نصوص لمعالجة مشكلة numpy.int64
            string_emp_codes = []
            for code in housing_df['emp_code'].unique():
                string_emp_codes.append(str(code))
            
            logger.info(f"عدد الموظفين الفريدين في البيانات: {len(string_emp_codes)}")
            
            # البحث عن سجلات الموظفين الموجودة مسبقاً باستخدام السلاسل النصية
            existing_employees = {e.emp_code: e for e in Employee.query.filter(Employee.emp_code.in_(string_emp_codes)).all()}
            logger.info(f"تم العثور على {len(existing_employees)} موظف موجود في قاعدة البيانات")
            
            # التأكد من وجود قسم HOUSING
            housing_dept = Department.query.filter_by(dept_id="10").first()
            if not housing_dept:
                housing_dept = Department(dept_id="10", name="HOUSING", active=True)
                db.session.add(housing_dept)
                db.session.commit()
                logger.info("تم إنشاء قسم HOUSING")
            
            # تحويل البيانات إلى التنسيق المناسب لمعالجتها
            attendance_data = {}  # {(emp_code, date): {'clock_in': time, 'clock_out': time, ...}}
            
            # معالجة كل صف في البيانات
            for _, row in housing_df.iterrows():
                try:
                    emp_code = str(row['emp_code']).strip()  # تحويل إلى نص لتجنب مشكلة numpy.int64
                    if not emp_code:
                        continue
                        
                    # استخراج التاريخ والوقت وحالة البصمة
                    try:
                        att_date = pd.to_datetime(row['att_date']).date()
                        punch_time = pd.to_datetime(f"{row['att_date']} {row['punch_time']}")
                        punch_state = str(row.get('punch_state', '')).lower()
                        terminal_alias = str(row.get('terminal_alias', ''))
                    except Exception as date_error:
                        logger.warning(f"خطأ في تحويل التاريخ أو الوقت: {str(date_error)} - {row['att_date']} {row['punch_time']}")
                        continue
                        
                    # تخزين البيانات حسب الموظف والتاريخ
                    key = (emp_code, att_date)
                    if key not in attendance_data:
                        attendance_data[key] = {
                            'clock_in': None, 
                            'clock_out': None,
                            'terminal_alias_in': None,
                            'terminal_alias_out': None,
                            'first_name': row.get('first_name', f"Employee {emp_code}"),
                            'all_punches': []  # حفظ جميع البصمات لهذا اليوم
                        }
                    
                    # حفظ جميع البصمات للمعالجة لاحقاً
                    attendance_data[key]['all_punches'].append({
                        'time': punch_time,
                        'state': punch_state, 
                        'terminal': terminal_alias
                    })
                    
                except Exception as row_error:
                    logger.warning(f"خطأ في معالجة سجل: {str(row_error)}")
                    continue
            
            logger.info(f"تم تجميع {len(attendance_data)} سجل حضور للحفظ")
            
            # معالجة البصمات قبل الحفظ - أخذ أول وآخر بصمة لكل يوم
            for key, data in attendance_data.items():
                if 'all_punches' in data and data['all_punches']:
                    # ترتيب البصمات حسب الوقت
                    punches = sorted(data['all_punches'], key=lambda x: x['time'])
                    
                    if punches:
                        # استخدام أول بصمة كـ clock_in
                        data['clock_in'] = punches[0]['time']
                        data['terminal_alias_in'] = punches[0]['terminal']
                        
                        # استخدام آخر بصمة كـ clock_out
                        data['clock_out'] = punches[-1]['time']
                        data['terminal_alias_out'] = punches[-1]['terminal']
                
                # حذف قائمة البصمات من الذاكرة لتوفير المساحة
                if 'all_punches' in data:
                    del data['all_punches']
            
        except Exception as e:
            error_msg = f"خطأ في تحضير البيانات للحفظ: {str(e)}"
            logger.error(error_msg)
            sync_log.status = "error"
            sync_log.error_message = error_msg
            db.session.commit()
            SYNC_PROGRESS["status"] = "error"
            SYNC_PROGRESS["error"] = error_msg
            return 0
            
        # التحقق من الإلغاء
        if check_cancellation(sync_log, db):
            return 0
            
        # 8. حفظ البيانات في قاعدة البيانات
        update_sync_status("save", 80, "جاري حفظ البيانات في قاعدة البيانات...")
        
        try:
            total_records = len(attendance_data)
            batch_size = 50  # حجم الدفعة
            current_batch = 0
            saved_records = 0
            
            # تقسيم البيانات إلى دفعات للحفظ
            batches = [list(attendance_data.items())[i:i+batch_size] for i in range(0, total_records, batch_size)]
            
            for batch in batches:
                # التحقق من الإلغاء قبل معالجة كل دفعة
                if check_cancellation(sync_log, db):
                    return saved_records
                
                current_batch += 1
                batch_saved = 0
                
                try:
                    for (emp_code, att_date), data in batch:
                        # 1. العثور على الموظف أو إنشاؤه
                        employee = existing_employees.get(emp_code)
                        if not employee:
                            try:
                                # إنشاء موظف جديد
                                employee = Employee(
                                    emp_code=emp_code,
                                    name=data.get('first_name', f"Employee {emp_code}"),
                                    department_id=housing_dept.id
                                )
                                db.session.add(employee)
                                db.session.flush()  # الحصول على المعرف بعد الإضافة
                                existing_employees[emp_code] = employee
                                logger.info(f"تم إنشاء موظف جديد: {emp_code}")
                            except Exception as emp_error:
                                logger.error(f"خطأ في إنشاء موظف جديد: {str(emp_error)}")
                                continue
                        
                        # 2. البحث عن سجل حضور موجود أو إنشاء سجل جديد
                        try:
                            attendance = AttendanceRecord.query.filter_by(
                                employee_id=employee.id,
                                date=att_date
                            ).first()
                            
                            # حساب ساعات العمل والوقت الإجمالي
                            standard_hours = employee.daily_hours or 8  # نستخدم 8 ساعات كقيمة افتراضية
                            clock_in = data.get('clock_in')
                            clock_out = data.get('clock_out')
                            
                            # تحديد ما إذا كان اليوم هو الجمعة أو الخميس
                            is_friday = att_date.weekday() == 4  # الجمعة هي 4 في نظام ترقيم Python
                            is_thursday = att_date.weekday() == 3  # الخميس هو 3 في نظام ترقيم Python
                            
                            # حساب الوقت الإجمالي كنص (HH:MM)
                            total_time = ""
                            work_hours = 0
                            overtime_hours = 0
                            
                            if clock_in and clock_out:
                                # حساب الوقت الإجمالي
                                time_diff = clock_out - clock_in
                                total_seconds = time_diff.total_seconds()
                                
                                # تقريب الساعات إلى أقرب ربع ساعة
                                total_hours = total_seconds / 3600
                                total_hours_rounded = round(total_hours * 4) / 4
                                
                                hours = int(total_hours_rounded)
                                minutes = int((total_hours_rounded - hours) * 60)
                                total_time = f"{hours:d}:{minutes:02d}"
                                
                                # حساب ساعات العمل والإضافي مع مراعاة يوم الجمعة والخميس
                                work_hours, overtime_hours = calculate_work_hours(
                                    clock_in, 
                                    clock_out, 
                                    standard_hours, 
                                    is_friday=is_friday, 
                                    is_thursday=is_thursday,
                                    friday_hours=8  # ساعات العمل الافتراضية ليوم الجمعة
                                )
                                
                                # تنسيق الأرقام - إزالة الأصفار غير اللازمة بعد النقطة العشرية
                                if work_hours == int(work_hours):
                                    work_hours = int(work_hours)
                                else:
                                    # تقريب القيم مثل 1.15 إلى 1.2
                                    work_hours = round(work_hours * 10) / 10
                                
                                if overtime_hours == int(overtime_hours):
                                    overtime_hours = int(overtime_hours)
                                else:
                                    # تقريب القيم مثل 1.15 إلى 1.2
                                    overtime_hours = round(overtime_hours * 10) / 10
                                
                            elif is_friday:
                                # للأيام الجمعة بدون بصمات (للموظفين غير المداومين)
                                work_hours = 8
                                overtime_hours = 0
                                total_time = "8:00"
                            
                            # تحديث أو إنشاء السجل
                            if attendance:
                                # تحديث سجل موجود
                                if clock_in:
                                    attendance.clock_in = clock_in
                                    attendance.terminal_alias_in = data.get('terminal_alias_in', '')
                                if clock_out:
                                    attendance.clock_out = clock_out
                                    attendance.terminal_alias_out = data.get('terminal_alias_out', '')
                                
                                attendance.total_time = total_time
                                attendance.work_hours = work_hours
                                attendance.overtime_hours = overtime_hours
                                attendance.attendance_status = 'P'  # تعيين الحالة كحاضر
                                attendance.updated_at = datetime.utcnow()
                            else:
                                # إنشاء سجل جديد
                                attendance = AttendanceRecord(
                                    employee_id=employee.id,
                                    date=att_date,
                                    weekday=att_date.strftime('%A'),
                                    clock_in=clock_in,
                                    clock_out=clock_out,
                                    terminal_alias_in=data.get('terminal_alias_in', ''),
                                    terminal_alias_out=data.get('terminal_alias_out', ''),
                                    total_time=total_time,
                                    work_hours=work_hours,
                                    overtime_hours=overtime_hours,
                                    attendance_status='P' if (clock_in or clock_out) else 'A'
                                )
                                db.session.add(attendance)
                            
                            batch_saved += 1
                            saved_records += 1
                            
                        except Exception as att_error:
                            logger.error(f"خطأ في معالجة سجل الحضور: {str(att_error)}")
                            continue
                    
                    # حفظ الدفعة الحالية
                    db.session.commit()
                    logger.info(f"تم حفظ الدفعة {current_batch}/{len(batches)} بنجاح ({batch_saved} سجل)")
                    
                    # تحديث التقدم
                    progress = 80 + int((current_batch / len(batches)) * 15)
                    update_sync_status("save", progress, f"تم حفظ {saved_records}/{total_records} سجل...")
                    
                except SQLAlchemyError as batch_error:
                    db.session.rollback()
                    logger.error(f"خطأ في حفظ الدفعة {current_batch}: {str(batch_error)}")
                    continue
            
            # تحديث سجل المزامنة بعدد السجلات المحفوظة
            sync_log.records_synced = saved_records
            synced_records = saved_records
            
            # إكمال المزامنة بنجاح
            sync_log.status = "success" 
            sync_log.step = "complete"
            sync_log.end_time = datetime.utcnow()
            db.session.commit()
            
            update_sync_status("complete", 100, f"اكتملت المزامنة بنجاح! {saved_records} سجل", records=saved_records, status="success")
            
            logger.info(f"اكتملت المزامنة بنجاح: تم حفظ {saved_records}/{total_records} سجل")
            
        except Exception as save_error:
            error_msg = f"خطأ عام أثناء حفظ البيانات: {str(save_error)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            sync_log.status = "error"
            sync_log.error_message = error_msg
            sync_log.end_time = datetime.utcnow()
            db.session.commit()
            SYNC_PROGRESS["status"] = "error"
            SYNC_PROGRESS["error"] = error_msg
            return saved_records
        
        # التنظيف النهائي وإزالة الملف المؤقت
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"تم حذف الملف المؤقت: {temp_file}")
        except Exception as cleanup_error:
            logger.warning(f"فشل في حذف الملف المؤقت: {str(cleanup_error)}")
        
        return synced_records
        
    except Exception as e:
        # معالجة الاستثناءات غير المتوقعة
        error_msg = f"خطأ غير متوقع في عملية المزامنة: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        if sync_log:
            sync_log.status = "error"
            sync_log.error_message = error_msg
            sync_log.end_time = datetime.utcnow()
            db.session.commit()
        
        SYNC_PROGRESS["status"] = "error"
        SYNC_PROGRESS["error"] = error_msg
        return synced_records
    
    finally:
        # إزالة سياق التطبيق إذا تم دفعه
        if ctx:
            ctx.pop()

def start_sync_in_background(app=None):
    """بدء المزامنة في خيط منفصل مع تتبع حالتها"""
    global SYNC_THREAD, CANCEL_SYNC
    
    # إلغاء أي مزامنة جارية
    cancel_sync()
    
    # إعادة تعيين حالة المزامنة
    reset_sync_state()
    
    # إنشاء خيط جديد للمزامنة
    SYNC_THREAD = threading.Thread(
        target=simple_sync_data,
        kwargs={'app': app}
    )
    SYNC_THREAD.daemon = True
    SYNC_THREAD.start()
    
    logger.info("تم بدء المزامنة في الخلفية")
    return True

def cancel_sync():
    """إلغاء عملية المزامنة الجارية"""
    global CANCEL_SYNC, SYNC_THREAD, SYNC_PROGRESS
    
    if SYNC_THREAD and SYNC_THREAD.is_alive():
        CANCEL_SYNC = True
        logger.info("تم إرسال طلب إلغاء المزامنة")
        SYNC_PROGRESS["status"] = "cancelling"
        SYNC_PROGRESS["message"] = "جاري إلغاء المزامنة..."
        
        # انتظار انتهاء الخيط (بحد أقصى 5 ثواني)
        SYNC_THREAD.join(5)
        return True
    else:
        logger.info("لا توجد عملية مزامنة جارية للإلغاء")
        return False

def get_sync_status():
    """الحصول على حالة المزامنة الحالية"""
    global SYNC_PROGRESS
    return SYNC_PROGRESS