"""
عرض قائمة الموظفين لمساعدة المستخدم في العثور على الموظف المطلوب
"""
from app import app
from models import db, Employee
import sys

search_term = "2713"  # البحث عن الموظفين بالرمز المشابه

with app.app_context():
    print(f"البحث عن الموظفين بالرمز المشابه: {search_term}")
    
    # البحث عن موظفين برموز تحتوي على الرقم المحدد
    similar_employees = Employee.query.filter(
        Employee.emp_code.like(f"%{search_term}%")
    ).all()
    
    if similar_employees:
        print(f"\nالموظفون ذوي الرموز المشابهة لـ '{search_term}' ({len(similar_employees)}):")
        print("=" * 60)
        print("الرمز\tالاسم\t\t\tالحالة")
        print("-" * 60)
        for emp in similar_employees:
            print(f"{emp.emp_code}\t{emp.name:<20}\t{'نشط' if emp.active else 'غير نشط'}")
    else:
        # توسيع البحث إلى رموز أقل دقة
        print(f"لا يوجد موظفون برموز تتضمن '{search_term}'")
        
        # عرض قائمة الموظفين البدء بالرقم 27
        similar_employees = Employee.query.filter(
            Employee.emp_code.like("27%")
        ).all()
        
        if similar_employees:
            print(f"\nالموظفون الذين تبدأ رموزهم بـ '27' ({len(similar_employees)}):")
            print("=" * 60)
            print("الرمز\tالاسم\t\t\tالحالة")
            print("-" * 60)
            for emp in similar_employees:
                print(f"{emp.emp_code}\t{emp.name:<20}\t{'نشط' if emp.active else 'غير نشط'}")
        else:
            print("لا يوجد موظفون برموز تبدأ بـ '27'")
            
            # عرض أول 20 موظف
            print("\nقائمة بأول 20 موظف في النظام:")
            print("=" * 60)
            print("الرمز\tالاسم\t\t\tالقسم\t\tالحالة")
            print("-" * 60)
            employees = Employee.query.limit(20).all()
            for emp in employees:
                dept_name = emp.department.name if emp.department else "غير محدد"
                print(f"{emp.emp_code}\t{emp.name:<20}\t{dept_name:<10}\t{'نشط' if emp.active else 'غير نشط'}")
