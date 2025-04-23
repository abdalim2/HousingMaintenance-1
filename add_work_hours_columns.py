"""
سكريبت ترحيل قاعدة البيانات لإضافة أعمدة ساعات العمل والوقت الإضافي
لجدول سجلات الحضور attendance_records

قم بتشغيل هذا السكريبت مرة واحدة لتحديث هيكل قاعدة البيانات.
"""
import os
import sys
import logging
from flask import Flask
from sqlalchemy import text
from database import db, init_db

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """إنشاء تطبيق Flask للعمليات على قاعدة البيانات"""
    app = Flask(__name__)
    
    # استخدام نفس إعدادات قاعدة البيانات كما في app.py
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 15,
        "connect_args": {
            "sslmode": "require"
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # تهيئة اتصال قاعدة البيانات
    init_db(app)
    
    return app

def add_work_hours_columns():
    """إضافة أعمدة ساعات العمل والوقت الإضافي إلى جدول attendance_records إذا لم تكن موجودة"""
    try:
        app = create_app()
        with app.app_context():
            conn = db.engine.connect()
            
            # التحقق مما إذا كانت الأعمدة موجودة بالفعل
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('attendance_records')]
            
            # إضافة عمود work_hours إذا لم يكن موجودًا
            if 'work_hours' not in columns:
                logger.info("إضافة عمود work_hours إلى جدول attendance_records...")
                try:
                    with conn.begin():
                        conn.execute(text("ALTER TABLE attendance_records ADD COLUMN work_hours FLOAT DEFAULT 0.0"))
                        logger.info("تم إضافة عمود work_hours بنجاح")
                except Exception as e:
                    logger.error(f"خطأ أثناء إضافة عمود work_hours: {str(e)}")
                    return False
            else:
                logger.info("عمود work_hours موجود بالفعل - لا حاجة للترحيل")
            
            # إضافة عمود overtime_hours إذا لم يكن موجودًا
            if 'overtime_hours' not in columns:
                logger.info("إضافة عمود overtime_hours إلى جدول attendance_records...")
                try:
                    with conn.begin():
                        conn.execute(text("ALTER TABLE attendance_records ADD COLUMN overtime_hours FLOAT DEFAULT 0.0"))
                        logger.info("تم إضافة عمود overtime_hours بنجاح")
                except Exception as e:
                    logger.error(f"خطأ أثناء إضافة عمود overtime_hours: {str(e)}")
                    return False
            else:
                logger.info("عمود overtime_hours موجود بالفعل - لا حاجة للترحيل")
            
            logger.info("اكتمل ترحيل قاعدة البيانات بنجاح!")
            conn.close()
            return True
    except Exception as e:
        logger.error(f"خطأ أثناء الترحيل: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("بدء ترحيل قاعدة البيانات...")
    
    success = add_work_hours_columns()
    
    if success:
        logger.info("اكتمل ترحيل قاعدة البيانات بنجاح!")
        sys.exit(0)
    else:
        logger.error("فشل ترحيل قاعدة البيانات!")
        sys.exit(1)