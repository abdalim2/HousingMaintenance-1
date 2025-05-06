
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
    """إنشاء تطبيق Flask للعمليات على قاعدة البيانات"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/biometric_sync.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_db(app)
    return app

def add_indexes_to_db():
    """إضافة فهارس لتحسين أداء قاعدة البيانات"""
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

if __name__ == "__main__":
    logger.info("جاري إضافة فهارس لتحسين أداء قاعدة البيانات...")
    success = add_indexes_to_db()
    if success:
        logger.info("تمت إضافة الفهارس بنجاح!")
        sys.exit(0)
    else:
        logger.error("فشلت عملية إضافة الفهارس!")
        sys.exit(1)
