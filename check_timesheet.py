from database import db
from flask import Flask, request_started, g
from models import Department, Employee, AttendanceRecord
import datetime
from optimized_timesheet import optimized_generate_timesheet

class FakeRequest:
    """فئة وهمية تمثل كائن الطلب"""
    
    @property
    def args(self):
        """إرجاع قاموس فارغ للوسائط"""
        return {}

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
db.init_app(app)

with app.app_context():
    # إنشاء سياق وهمي للطلب
    g.request = FakeRequest()
    
    # تحديد الشهر والسنة الحالية
    now = datetime.datetime.now()
    year = "2025"
    month = "5"  # شهر مايو
    
    # طلب بيانات timesheet من أجل شهر مايو
    print(f"طلب بيانات الدوام لشهر {month} وسنة {year}")
    try:
        # استخدام try/except لالتقاط أي أخطاء قد تحدث
        timesheet_data = optimized_generate_timesheet(year, month, None, None, None, None, force_refresh=True)
    except Exception as e:
        print(f"حدث خطأ: {e}")
        
        # محاولة استخدام دالة أخرى للحصول على البيانات
        try:
            from data_processor import generate_timesheet
            print("محاولة استخدام generate_timesheet بدلاً من optimized_generate_timesheet")
            timesheet_data = generate_timesheet(year, month, None, None, None, None, force_refresh=True)
        except Exception as e2:
            print(f"حدث خطأ آخر: {e2}")
            timesheet_data = None
    
    # طباعة معلومات عن timesheet
    if timesheet_data:
        print(f"تم استلام البيانات - عدد الموظفين: {len(timesheet_data.get('employees', []))}")
        print(f"التواريخ في الشهر: {len(timesheet_data.get('dates', []))}")
        
        # طباعة التواريخ للتحقق
        dates = timesheet_data.get('dates', [])
        print(f"التواريخ المتاحة: {[d.strftime('%Y-%m-%d') for d in dates]}")
        
        # التحقق من وجود تاريخ 11-5-2025
        if datetime.date(2025, 5, 11) in dates:
            print("تاريخ 11-5-2025 موجود في قائمة التواريخ")
        else:
            print("تاريخ 11-5-2025 غير موجود في قائمة التواريخ")
        
        # التحقق من بيانات حضور أول موظف في اليوم المطلوب
        employees = timesheet_data.get('employees', [])
        if employees:
            first_employee = employees[0]
            print(f"\nبيانات أول موظف: {first_employee.get('name')}")
            
            # التحقق من بيانات الحضور
            attendance = first_employee.get('attendance', [])
            for att in attendance:
                if att.get('date_str') == '2025-05-11':
                    print(f"سجل الحضور ليوم 11-5-2025: {att}")
                    break
            else:
                print("لم يتم العثور على سجل حضور لهذا اليوم للموظف الأول")
                
                # فحص جميع مفاتيح السجل للتأكد من تنسيق التاريخ
                if attendance:
                    print(f"أمثلة على مفاتيح التواريخ: {[att.get('date_str') for att in attendance[:3]]}")
    else:
        print("لم يتم استلام أي بيانات timesheet!")
