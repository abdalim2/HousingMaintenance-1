import os
import sys
import logging
from flask import Flask
from sqlalchemy import Index
from database import db, init_db
from models import EmployeeVacation, EmployeeTransfer

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """إنشاء تطبيق Flask للعمليات على قاعدة البيانات"""
    app = Flask(__name__)
    
    # Get database URL from environment or use default
    database_url = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    init_db(app)
    return app

def add_indexes_to_vacation_transfer():
    """إضافة فهارس لتحسين أداء جداول الإجازات والتنقلات"""
    try:
        app = create_app()
        with app.app_context():
            # إضافة فهرس على جدول EmployeeVacation
            idx_vacation_employee = Index('idx_vacation_employee', EmployeeVacation.employee_id)
            idx_vacation_start_date = Index('idx_vacation_start_date', EmployeeVacation.start_date)
            idx_vacation_end_date = Index('idx_vacation_end_date', EmployeeVacation.end_date)
            idx_vacation_emp_date_range = Index('idx_vacation_emp_date_range', 
                                             EmployeeVacation.employee_id, 
                                             EmployeeVacation.start_date,
                                             EmployeeVacation.end_date)
            
            # إضافة فهرس على جدول EmployeeTransfer
            idx_transfer_employee = Index('idx_transfer_employee', EmployeeTransfer.employee_id)
            idx_transfer_start_date = Index('idx_transfer_start_date', EmployeeTransfer.start_date)
            idx_transfer_end_date = Index('idx_transfer_end_date', EmployeeTransfer.end_date)
            idx_transfer_emp_date_range = Index('idx_transfer_emp_date_range', 
                                             EmployeeTransfer.employee_id, 
                                             EmployeeTransfer.start_date,
                                             EmployeeTransfer.end_date)
            
            # إضافة فهارس إضافية للتنقلات
            idx_transfer_from_dept = Index('idx_transfer_from_dept', EmployeeTransfer.from_department_id)
            idx_transfer_to_dept = Index('idx_transfer_to_dept', EmployeeTransfer.to_department_id)
            idx_transfer_from_housing = Index('idx_transfer_from_housing', EmployeeTransfer.from_housing_id)
            idx_transfer_to_housing = Index('idx_transfer_to_housing', EmployeeTransfer.to_housing_id)
            
            # إنشاء جميع الفهارس
            all_indexes = [
                idx_vacation_employee, idx_vacation_start_date, idx_vacation_end_date, idx_vacation_emp_date_range,
                idx_transfer_employee, idx_transfer_start_date, idx_transfer_end_date, idx_transfer_emp_date_range,
                idx_transfer_from_dept, idx_transfer_to_dept, idx_transfer_from_housing, idx_transfer_to_housing
            ]
            
            for idx in all_indexes:
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
    logger.info("جاري إضافة فهارس لتحسين أداء جداول الإجازات والتنقلات...")
    success = add_indexes_to_vacation_transfer()
    if success:
        logger.info("تمت إضافة الفهارس بنجاح!")
        sys.exit(0)
    else:
        logger.error("فشلت عملية إضافة الفهارس!")
        sys.exit(1)
