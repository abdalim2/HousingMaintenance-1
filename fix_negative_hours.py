"""
سكريبت بسيط لإصلاح سجلات البصمات التي تحتوي على ساعات عمل سالبة
عن طريق تبديل بصمات الدخول والخروج
"""

from app import app, db
from models import AttendanceRecord
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_negative_work_hours():
    """إصلاح سجلات الساعات السالبة عن طريق تبديل بصمات الدخول والخروج"""
    
    with app.app_context():
        # البحث عن السجلات ذات ساعات العمل السالبة
        negative_records = AttendanceRecord.query.filter(AttendanceRecord.work_hours < 0).all()
        logger.info(f"تم العثور على {len(negative_records)} سجل بساعات عمل سالبة")
        
        if not negative_records:
            logger.info("لا توجد سجلات تحتاج إلى إصلاح")
            return True
            
        # تصحيح السجلات عن طريق تبديل بصمات الدخول والخروج
        for record in negative_records:
            try:
                # عرض بيانات السجل قبل التعديل
                logger.info(f"قبل التعديل - سجل #{record.id}: موظف {record.employee_id}, تاريخ {record.date}, "
                           f"دخول {record.clock_in}, خروج {record.clock_out}, ساعات {record.work_hours}")
                
                # تبديل بصمة الدخول والخروج
                temp_in = record.clock_in
                temp_alias_in = record.terminal_alias_in
                
                record.clock_in = record.clock_out
                record.terminal_alias_in = record.terminal_alias_out
                
                record.clock_out = temp_in
                record.terminal_alias_out = temp_alias_in
                
                # إعادة حساب ساعات العمل
                time_diff = record.clock_out - record.clock_in
                hours = time_diff.total_seconds() / 3600
                record.work_hours = round(hours, 2)
                
                hours_int = int(hours)
                minutes = int((hours - hours_int) * 60)
                record.total_time = f"{hours_int}:{minutes:02d}"
                
                # عرض بيانات السجل بعد التعديل
                logger.info(f"بعد التعديل - سجل #{record.id}: موظف {record.employee_id}, تاريخ {record.date}, "
                           f"دخول {record.clock_in}, خروج {record.clock_out}, ساعات {record.work_hours}")
                
            except Exception as e:
                logger.error(f"خطأ في معالجة السجل #{record.id}: {str(e)}")
        
        # حفظ التغييرات في قاعدة البيانات
        db.session.commit()
        logger.info(f"تم تحديث {len(negative_records)} سجل بنجاح")
        
        # التحقق من أن جميع السجلات تم إصلاحها
        remaining = AttendanceRecord.query.filter(AttendanceRecord.work_hours < 0).count()
        if remaining > 0:
            logger.warning(f"لا يزال هناك {remaining} سجل بساعات سالبة")
        else:
            logger.info("تم إصلاح جميع السجلات بنجاح")
            
        return True

if __name__ == "__main__":
    logger.info("بدء إصلاح سجلات الساعات السالبة...")
    
    success = fix_negative_work_hours()
    
    if success:
        logger.info("اكتملت عملية الإصلاح!")
    else:
        logger.error("فشلت عملية الإصلاح!")