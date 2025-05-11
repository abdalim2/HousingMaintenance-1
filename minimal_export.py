from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
import copy
import logging
from optimized_timesheet import optimized_generate_timesheet

# تعريف مسار للتصدير البسيط للدوام
def export_minimal_timesheet(app):
    @app.route('/export_minimal_timesheet', methods=['GET'])
    def export_minimal_timesheet():
        """تصدير كشف الدوام بتنسيق بسيط للطباعة"""        # الحصول على المعلمات من عنوان الطلب
        year = request.args.get('year')
        month = request.args.get('month')
        dept_id = request.args.get('department')
        housing_id = request.args.get('housing')
        autoprint = request.args.get('autoprint', 'false')
        
        # طباعة معلومات تصحيح الأخطاء
        print(f"*** تصدير PDF للدوام: سنة={year}, شهر={month}, قسم={dept_id}, سكن={housing_id}")
        
        try:
            # إجبار إعادة تحميل البيانات للحصول على أحدث المعلومات
            timesheet_data = optimized_generate_timesheet(
                year, month, dept_id, None, None, housing_id, force_refresh=True
            )
            
            # معالجة بيانات الموظفين والتواريخ
            employees = timesheet_data.get('employees', [])
            dates = timesheet_data.get('dates', [])
            weekend_days = timesheet_data.get('weekend_days', [5, 6])  # الجمعة والسبت افتراضياً
            
            # إضافة معلومات التاريخ بتنسيق سلسلة نصية لكل سجل حضور
            for employee in employees:
                for att in employee.get('attendance', []):
                    if 'date' in att:
                        try:
                            if hasattr(att['date'], 'strftime'):
                                att['date_str'] = att['date'].strftime('%Y-%m-%d')
                            else:
                                att['date_str'] = str(att['date'])
                        except Exception as e:
                            print(f"خطأ في معالجة تاريخ الحضور: {e}")
            
            # الحصول على اسم القسم إذا تم تحديده
            from models import Department, Housing
            department_name = "كل الأقسام"
            if dept_id:
                dept = Department.query.get(dept_id)
                if dept:
                    department_name = dept.name
            
            # الحصول على اسم السكن إذا تم تحديده
            housing_name = "كل السكنات"
            if housing_id:
                housing = Housing.query.get(housing_id)
                if housing:
                    housing_name = housing.name
              # طباعة المعلومات التشخيصية
            print(f"معلومات كشف الدوام: {len(employees)} موظف، {len(dates)} يوم")
            if employees and len(employees) > 0:
                print(f"عدد سجلات حضور الموظف الأول: {len(employees[0].get('attendance', []))}")
                print(f"معلومات الموظف الأول: {employees[0].get('name')}")
                # فحص سجلات الحضور
                first_emp_attendance = employees[0].get('attendance', [])
                if first_emp_attendance:
                    print(f"أول سجل حضور: {first_emp_attendance[0]}")
                    if 'status' in first_emp_attendance[0]:
                        print(f"حالة أول سجل: {first_emp_attendance[0].get('status')}")
            
            # نضمن أن لكل موظف ساعات عمل إجمالية
            for emp in employees:
                if 'total_work_hours' not in emp or emp['total_work_hours'] is None:
                    # حساب مجموع ساعات العمل من سجلات الحضور
                    total_hours = 0
                    present_days = 0
                    for att in emp.get('attendance', []):
                        if att.get('status') == 'P':  # حاضر
                            total_hours += att.get('work_hours', 8)  # افتراضياً 8 ساعات
                            present_days += 1
                    
                    emp['total_work_hours'] = total_hours
                    emp['present_days'] = present_days            # إنشاء نسخة عميقة من البيانات لتجنب أي تعديلات أثناء عرض القالب
            employees_copy = copy.deepcopy(employees)
            dates_copy = copy.deepcopy(dates)
            
            # تعريف دالة now() لاستخدامها في القالب
            def now():
                return datetime.now()
              # عرض القالب البسيط مع البيانات
            return render_template(
                'minimal_timesheet.html',
                employees=employees_copy,
                dates=dates_copy,
                weekend_days=weekend_days,
                department_name=department_name,
                housing_name=housing_name,
                month_name=timesheet_data.get('month_name', ''),
                year=timesheet_data.get('year', ''),
                autoprint=autoprint,
                now=now,
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"*** خطأ في تصدير الدوام: {e}")
            # إعادة التوجيه إلى صفحة كشف الدوام العادية
            return redirect(url_for('timesheet', year=year, month=month, department=dept_id, housing=housing_id))
    
    return export_minimal_timesheet

# لتسجيل المسار في تطبيق Flask
def register_minimal_export(app):
    export_minimal_timesheet(app)
    print("✅ تم تسجيل مسار التصدير البسيط بنجاح")
