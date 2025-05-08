"""
التحقق من حالة الموظف المفقود وإضافته إذا لزم الأمر
"""
from app import app
from models import db, Employee, Department
import sys

emp_code_to_check = "27133"

with app.app_context():
    # البحث عن الموظف بالرمز الدقيق
    employee = Employee.query.filter_by(emp_code=emp_code_to_check).first()
    
    if employee:
        print(f"الموظف موجود: {employee.emp_code} - {employee.name}")
        print(f"القسم: {employee.department.name if employee.department else 'غير محدد'}")
        print(f"حالة النشاط: {'نشط' if employee.active else 'غير نشط'}")
    else:
        print(f"الموظف برمز {emp_code_to_check} غير موجود")
        
        # البحث عن موظفين برموز مشابهة
        similar_employees = Employee.query.filter(
            Employee.emp_code.like(f"{emp_code_to_check[:3]}%")
        ).all()
        
        if similar_employees:
            print("\nالموظفون بالرموز المشابهة:")
            for emp in similar_employees:
                print(f"{emp.emp_code} - {emp.name} - {'نشط' if emp.active else 'غير نشط'}")
            
            # البحث بالحرفين الأولين فقط
            if len(similar_employees) == 0:
                similar_employees = Employee.query.filter(
                    Employee.emp_code.like(f"{emp_code_to_check[:2]}%")
                ).all()
                
                if similar_employees:
                    print("\nالموظفون بأول رقمين مشابهين:")
                    for emp in similar_employees:
                        print(f"{emp.emp_code} - {emp.name} - {'نشط' if emp.active else 'غير نشط'}")
        else:
            print("لا يوجد موظفون برموز مشابهة")
