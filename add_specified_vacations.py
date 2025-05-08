"""
سكريبت لإضافة بيانات الإجازات المحددة إلى جدول الإجازات
"""
from app import app
from models import db, Employee, EmployeeVacation
from datetime import datetime

# بيانات الإجازات المراد إضافتها
# الصيغة: CN, START DATE, END DATE
vacation_data = [
    ('39988', '20/01/2025', '20/01/2025'),
    ('33966', '13/10/2024', '22/01/2025'),
    ('39710', '01/02/2025', '01/02/2025'),
    ('30556', '13/12/2024', '08/02/2025'),
    ('28590', '08/02/2025', '10/02/2025'),
    ('27990', '28/11/2024', '14/02/2025'),
    ('41503', '15/02/2025', '21/02/2025'),
    ('39710', '23/02/2025', '24/02/2025'),
    ('27133', '24/12/2024', '11/03/2025'),
    ('39710', '03/04/2025', '05/04/2025'),
    ('49776', '18/02/2025', '18/04/2025'),
    ('29820', '26/04/2025', '10/05/2025'),
    ('31435', '18/03/2025', '13/05/2025'),
    ('40666', '30/03/2025', '22/05/2025'),
    ('28824', '30/04/2025', '29/05/2025'),
    ('37475', '24/03/2025', '08/06/2025')
]

# تحويل التواريخ من الصيغة dd/mm/yyyy إلى yyyy-mm-dd
def convert_date(date_str):
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        print(f"خطأ في تنسيق التاريخ: {date_str}")
        return None

# إضافة الإجازات إلى قاعدة البيانات
with app.app_context():
    print("بدء إضافة بيانات الإجازات...")
    added_count = 0
    error_count = 0
    employee_not_found = 0
    
    for emp_code, start_date_str, end_date_str in vacation_data:
        # البحث عن الموظف بواسطة الرمز
        employee = Employee.query.filter_by(emp_code=emp_code).first()
        
        if not employee:
            print(f"⚠️ الموظف برمز {emp_code} غير موجود في قاعدة البيانات")
            employee_not_found += 1
            continue
            
        # تحويل التواريخ
        start_date = convert_date(start_date_str)
        end_date = convert_date(end_date_str)
        
        if not start_date or not end_date:
            error_count += 1
            continue
            
        # التحقق من عدم وجود إجازة متطابقة
        existing_vacation = EmployeeVacation.query.filter_by(
            employee_id=employee.id,
            start_date=start_date,
            end_date=end_date
        ).first()
        
        if existing_vacation:
            print(f"⚠️ الإجازة للموظف {employee.name} ({emp_code}) من {start_date} إلى {end_date} موجودة بالفعل")
            continue
            
        # إنشاء سجل الإجازة الجديد
        try:
            vacation = EmployeeVacation(
                employee_id=employee.id,
                start_date=start_date,
                end_date=end_date,
                notes=f"تمت إضافة الإجازة بتاريخ {datetime.now().strftime('%Y-%m-%d')}"
            )
            db.session.add(vacation)
            added_count += 1
            print(f"✓ تمت إضافة إجازة للموظف {employee.name} ({emp_code}) من {start_date} إلى {end_date}")
        except Exception as e:
            print(f"❌ خطأ أثناء إضافة الإجازة للموظف {emp_code}: {str(e)}")
            error_count += 1
    
    # حفظ التغييرات
    if added_count > 0:
        db.session.commit()
        
    # عرض ملخص النتائج
    print("\n=== ملخص إضافة الإجازات ===")
    print(f"إجمالي الإجازات المطلوب إضافتها: {len(vacation_data)}")
    print(f"الإجازات التي تمت إضافتها بنجاح: {added_count}")
    print(f"الموظفين غير الموجودين: {employee_not_found}")
    print(f"الأخطاء: {error_count}")
    
    # عرض قائمة بجميع الإجازات الموجودة في النظام
    print("\n=== الإجازات الموجودة في النظام ===")
    
    all_vacations = EmployeeVacation.query.order_by(EmployeeVacation.start_date).all()
    print(f"إجمالي عدد سجلات الإجازات: {len(all_vacations)}")
    print("\nCN\tاسم الموظف\tتاريخ البداية\tتاريخ النهاية")
    print("-" * 70)
    
    for vacation in all_vacations:
        emp_code = vacation.employee.emp_code if vacation.employee else "غير معروف"
        emp_name = vacation.employee.name if vacation.employee else "غير معروف"
        start = vacation.start_date.strftime('%d/%m/%Y')
        end = vacation.end_date.strftime('%d/%m/%Y')
        print(f"{emp_code}\t{emp_name}\t{start}\t{end}")
