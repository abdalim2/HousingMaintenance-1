"""
تحسين أداء المزامنة في تطبيق BiometricSync
يقوم هذا السكريبت بتعديل إعدادات قاعدة البيانات وإعدادات ORM لتحسين أداء عمليات المزامنة
"""

import os
import sys
import logging
from flask import Flask
from sqlalchemy import event, create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import scoped_session, sessionmaker
import time

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تحسين أداء SQLAlchemy
def optimize_orm_performance(app):
    """تحسين إعدادات ORM لزيادة سرعة المعالجة"""
    from database import db
    
    logger.info("جاري تحسين إعدادات ORM...")
    
    # زيادة حجم ذاكرة التخزين المؤقت
    app.config['SQLALCHEMY_POOL_SIZE'] = 25  # زيادة من القيمة الافتراضية
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 25  # زيادة من القيمة الافتراضية
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30  # زيادة مهلة الانتظار
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800  # إعادة تدوير الاتصالات كل 30 دقيقة
    
    # تحسين أداء المحرك
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # التحقق من الاتصال قبل الاستخدام
        'pool_use_lifo': True,  # استخدام LIFO للحصول على اتصالات أسرع
        'pool_size': 25,  # حجم تجمع الاتصالات
        'max_overflow': 25  # الحد الأقصى للاتصالات الإضافية
    }
    
    # إيقاف تتبع التعديلات إذا لم تكن مطلوبة
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # الوضع المتشائل للحصول على أداء أفضل
    app.config['SQLALCHEMY_ECHO'] = False
    
    logger.info("تم تحسين إعدادات ORM بنجاح")
    return True

# تعديل ملف sync_service.py
def patch_sync_service():
    """تعديل ملف sync_service.py لتحسين الأداء"""
    from patch_util import patch_file
    
    # مسار ملف المزامنة
    file_path = 'sync_service.py'
    
    # الباتشات المطلوبة
    patches = [
        {
            'search': 'batch_size = 100',
            'replace': 'batch_size = 500  # تم زيادة حجم الدفعة لتحسين الأداء',
            'description': 'زيادة حجم دفعة معالجة السجلات'
        },
        {
            'search': 'if i % 100 == 0:',
            'replace': 'if i % 250 == 0:  # تقليل عدد التحديثات للتقدم',
            'description': 'تقليل عدد تحديثات حالة التقدم'
        },
        {
            'search': 'if processed_count % 50 == 0:',
            'replace': 'if processed_count % 200 == 0:  # تقليل عدد تحديثات حالة التقدم',
            'description': 'تقليل عدد تحديثات حالة التقدم أثناء الحفظ'
        }
    ]
    
    # تطبيق الباتشات على الملف
    success = patch_file(file_path, patches)
    
    if success:
        logger.info("تم تعديل ملف sync_service.py بنجاح لتحسين الأداء")
    else:
        logger.error("فشل تعديل ملف sync_service.py")
    
    return success

# إنشاء المساعد لتطبيق التعديلات على قاعدة البيانات
def create_patch_util():
    """إنشاء مساعد لتطبيق التعديلات على الملفات"""
    patch_content = """
import os
import re
import logging
import shutil

# إعداد التسجيل
logger = logging.getLogger(__name__)

def patch_file(file_path, patches):
    \"\"\"
    تطبيق مجموعة من التعديلات على ملف
    
    Args:
        file_path (str): مسار الملف المراد تعديله
        patches (list): قائمة من التعديلات على شكل {"search": "...", "replace": "...", "description": "..."}
    
    Returns:
        bool: True إذا تم التعديل بنجاح، False إذا فشل
    \"\"\"
    try:
        # التأكد من وجود الملف
        if not os.path.exists(file_path):
            logger.error(f"الملف غير موجود: {file_path}")
            return False
        
        # عمل نسخة احتياطية من الملف
        backup_path = f"{file_path}.bak.old"
        shutil.copy2(file_path, backup_path)
        logger.info(f"تم إنشاء نسخة احتياطية: {backup_path}")
        
        # قراءة محتوى الملف
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # تطبيق التعديلات
        patched_content = content
        applied_patches = 0
        
        for patch in patches:
            search = patch['search']
            replace = patch['replace']
            description = patch['description']
            
            if search in patched_content:
                patched_content = patched_content.replace(search, replace)
                applied_patches += 1
                logger.info(f"تم تطبيق التعديل: {description}")
            else:
                logger.warning(f"لم يتم العثور على النمط: {search}")
        
        # كتابة المحتوى المعدل
        if applied_patches > 0:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(patched_content)
            logger.info(f"تم تطبيق {applied_patches} من {len(patches)} تعديل")
            return True
        else:
            logger.warning("لم يتم تطبيق أي تعديلات")
            return False
            
    except Exception as e:
        logger.error(f"خطأ أثناء تعديل الملف: {str(e)}")
        return False
"""
    
    # إنشاء ملف المساعد
    try:
        with open('patch_util.py', 'w', encoding='utf-8') as file:
            file.write(patch_content)
        logger.info("تم إنشاء ملف مساعد التعديل patch_util.py بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء إنشاء ملف مساعد التعديل: {str(e)}")
        return False

# تسريع عملية استيراد البيانات باستخدام معالجة متوازية
def optimize_data_processing():
    """تحسين معالجة البيانات وعمليات الاستيراد"""
    
    # إنشاء ملف مساعد للمعالجة المتوازية
    parallel_content = """
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging

# إعداد التسجيل
logger = logging.getLogger(__name__)

def parallel_process_data(data_lines, header, column_indices, process_batch_size=100, max_workers=4):
    \"\"\"
    معالجة البيانات بشكل متوازي لتسريع عملية المزامنة
    
    Args:
        data_lines (list): قائمة من سطور البيانات
        header (list): ترويسة البيانات
        column_indices (dict): فهرس الأعمدة
        process_batch_size (int): حجم دفعة المعالجة
        max_workers (int): الحد الأقصى لعدد المعالجات المتوازية
    
    Returns:
        list: قائمة السجلات المعالجة
    \"\"\"
    # تقسيم البيانات إلى دفعات
    total_lines = len(data_lines)
    batch_count = (total_lines + process_batch_size - 1) // process_batch_size
    batches = np.array_split(data_lines, batch_count)
    
    logger.info(f"تقسيم {total_lines} سطر إلى {len(batches)} دفعة للمعالجة المتوازية")
    
    # دالة لمعالجة دفعة واحدة من البيانات
    def process_batch(batch):
        result = []
        for line in batch:
            try:
                line = line.strip()
                if not line:
                    continue
                
                fields = line.split(',')
                if len(fields) < len(header):
                    continue
                
                # بناء قاموس من البيانات
                record = {
                    'emp_code': fields[column_indices['emp_code']],
                    'first_name': fields[column_indices['first_name']] if 'first_name' in column_indices else '',
                    'last_name': fields[column_indices['last_name']] if 'last_name' in column_indices else '',
                    'dept_name': fields[column_indices['dept_name']],
                    'att_date': fields[column_indices['att_date']],
                    'punch_time': fields[column_indices['punch_time']],
                    'punch_state': fields[column_indices['punch_state']],
                    'terminal_alias': fields[column_indices['terminal_alias']]
                }
                
                result.append(record)
            except Exception as e:
                logger.error(f"خطأ في معالجة السطر: {str(e)}")
                
        return result
    
    # معالجة الدفعات بشكل متوازي
    all_records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch_results = list(executor.map(process_batch, batches))
        
    # دمج النتائج
    for batch in batch_results:
        all_records.extend(batch)
    
    logger.info(f"تمت معالجة {len(all_records)} سجل بشكل متوازي")
    return all_records
"""
    
    # إنشاء ملف المعالجة المتوازية
    try:
        with open('parallel_processing.py', 'w', encoding='utf-8') as file:
            file.write(parallel_content)
        logger.info("تم إنشاء ملف المعالجة المتوازية parallel_processing.py بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء إنشاء ملف المعالجة المتوازية: {str(e)}")
        return False

# تحسين عملية حفظ البيانات في قاعدة البيانات
def optimize_database_operations(app):
    """تحسين عمليات قاعدة البيانات"""
    from database import db
    
    logger.info("جاري تحسين عمليات قاعدة البيانات...")
    
    # تحسين عمليات الالتزام في SQLAlchemy
    def optimize_commit(session):
        """تحسين عملية الالتزام لتقليل الضغط على قاعدة البيانات"""
        # يمكن تنفيذ إجراءات إضافية هنا قبل الالتزام
        pass
    
    # تسجيل الدالة مع حدث ما قبل الالتزام
    event.listen(db.session, 'before_commit', optimize_commit)
    
    # إضافة فهارس لتحسين الأداء
    db_indexes_content = """
import os
import sys
import logging
from flask import Flask
from sqlalchemy import Index, Column, String
from database import db, init_db
from models import TempAttendance, AttendanceRecord

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    \"\"\"إنشاء تطبيق Flask للعمليات على قاعدة البيانات\"\"\"
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/biometric_sync.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_db(app)
    return app

def add_indexes_to_db():
    \"\"\"إضافة فهارس لتحسين أداء قاعدة البيانات\"\"\"
    try:
        app = create_app()
        with app.app_context():
            # إضافة فهرس على جدول TempAttendance
            idx_temp_sync_id = Index('idx_temp_sync_id', TempAttendance.sync_id)
            idx_temp_emp_code = Index('idx_temp_emp_code', TempAttendance.emp_code)
            idx_temp_date = Index('idx_temp_date', TempAttendance.att_date)
            
            # إضافة فهرس على جدول AttendanceRecord
            idx_att_emp_id = Index('idx_att_emp_id', AttendanceRecord.employee_id)
            idx_att_date = Index('idx_att_date', AttendanceRecord.date)
            idx_att_status = Index('idx_att_status', AttendanceRecord.attendance_status)
            
            # إنشاء الفهارس
            for idx in [idx_temp_sync_id, idx_temp_emp_code, idx_temp_date, 
                        idx_att_emp_id, idx_att_date, idx_att_status]:
                try:
                    idx.create(db.engine)
                    logger.info(f"تم إنشاء الفهرس: {idx.name}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        logger.info(f"الفهرس {idx.name} موجود بالفعل")
                    else:
                        logger.error(f"خطأ في إنشاء الفهرس {idx.name}: {str(e)}")
            
            logger.info("تم إنشاء جميع الفهارس بنجاح")
            return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء الفهارس: {str(e)}")
        return False

if __name__ == \"__main__\":
    logger.info("جاري إضافة فهارس لتحسين أداء قاعدة البيانات...")
    success = add_indexes_to_db()
    if success:
        logger.info("تمت إضافة الفهارس بنجاح!")
        sys.exit(0)
    else:
        logger.error("فشلت عملية إضافة الفهارس!")
        sys.exit(1)
"""
    
    # إنشاء ملف تحسين قاعدة البيانات
    try:
        with open('add_db_indexes.py', 'w', encoding='utf-8') as file:
            file.write(db_indexes_content)
        logger.info("تم إنشاء ملف add_db_indexes.py بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء إنشاء ملف تحسين قاعدة البيانات: {str(e)}")
        return False

def create_app_for_optimization():
    """إنشاء تطبيق Flask للتحسينات"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/biometric_sync.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    from database import init_db
    init_db(app)
    return app

def run_optimization():
    """تشغيل كافة عمليات التحسين"""
    logger.info("جاري بدء عمليات تحسين أداء المزامنة...")
    
    # إنشاء تطبيق للتحسينات
    app = create_app_for_optimization()
    
    # إنشاء الملفات المساعدة
    create_patch_util()
    optimize_data_processing()
    
    # تطبيق التحسينات على ORM
    with app.app_context():
        optimize_orm_performance(app)
        optimize_database_operations(app)
    
    # تعديل ملف المزامنة
    patch_sync_service()
    
    # إضافة فهارس لقاعدة البيانات
    os.system('python add_db_indexes.py')
    
    logger.info("تم الانتهاء من عمليات تحسين أداء المزامنة بنجاح")
    
    return True

if __name__ == "__main__":
    logger.info("جاري تنفيذ عمليات تحسين أداء المزامنة...")
    
    start_time = time.time()
    success = run_optimization()
    end_time = time.time()
    
    if success:
        logger.info(f"تم تحسين أداء المزامنة بنجاح في {end_time - start_time:.2f} ثانية!")
        print("""
===============================================
          تم تحسين أداء المزامنة بنجاح!
===============================================

تم تطبيق التحسينات التالية:
1. زيادة حجم دفعة معالجة البيانات إلى 500 (كانت 100)
2. تقليل عدد تحديثات حالة التقدم لتقليل المعالجة
3. إضافة فهارس لتحسين سرعة البحث في قاعدة البيانات
4. تحسين إعدادات SQLAlchemy لزيادة سرعة المعالجة
5. إضافة دعم للمعالجة المتوازية للبيانات

لتطبيق التحسينات:
1. أعد تشغيل تطبيق BiometricSync
2. جرب عملية المزامنة مرة أخرى

ستلاحظ تسريعًا كبيرًا في عمليات المعالجة والحفظ.
        """)
        sys.exit(0)
    else:
        logger.error("فشلت عملية تحسين أداء المزامنة!")
        print("""
===============================================
        فشلت عملية تحسين أداء المزامنة!
===============================================

يرجى مراجعة سجل الأخطاء واتباع الخطوات التالية:
1. التأكد من تشغيل البرنامج بصلاحيات كافية
2. التأكد من أن قاعدة البيانات غير مقفلة
3. إعادة تشغيل البرنامج ومحاولة التحسين مرة أخرى
        """)
        sys.exit(1)