import logging
import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import extract

# Configure logging
logger = logging.getLogger(__name__)

def get_current_year():
    """Get current year as string"""
    return str(datetime.now().year)

def get_current_month():
    """Get current month as string"""
    return str(datetime.now().month)

def get_month_name(month_num):
    """Convert month number to name"""
    return calendar.month_name[int(month_num)]

def get_day_name(weekday):
    """
    Get day name in English and Arabic based on weekday number (0-6, Monday is 0)
    
    Args:
        weekday: Integer representing day of week (0=Monday, 6=Sunday)
        
    Returns:
        String with day name
    """
    days_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_ar = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    
    if 0 <= weekday <= 6:
        return f"{days_en[weekday]} ({days_ar[weekday]})"
    else:
        return "Unknown"

def get_month_days(year, month):
    """
    Get number of days in month based on company's fiscal calendar
    
    Args:
        year: Year as integer or string
        month: Month as integer or string
    
    Returns:
        Number of days in the month
    """
    # Import here to avoid circular imports
    from models import MonthPeriod
    
    year = int(year)
    month = int(month)
    
    # Format month code to MM/YY format (e.g., "01/25" for January 2025)
    month_code = f"{month:02d}/{str(year)[2:4]}"
    
    # Try to find month period in the database
    month_period = MonthPeriod.query.filter_by(month_code=month_code).first()
    
    if month_period:
        # If found in database, use the days_in_month field
        return month_period.days_in_month
    else:
        # Fallback to standard calendar if not found
        return calendar.monthrange(year, month)[1]

def get_month_start_end_dates(year, month):
    """
    Get start and end dates for a month based on company's fiscal calendar
    
    Args:
        year: Year as integer or string
        month: Month as integer or string
    
    Returns:
        Tuple of (start_date, end_date) for the month
    """
    # Import here to avoid circular imports
    from models import MonthPeriod
    
    year = int(year)
    month = int(month)
    
    # Format month code to MM/YY format (e.g., "01/25" for January 2025)
    month_code = f"{month:02d}/{str(year)[2:4]}"
    
    # Try to find month period in the database
    month_period = MonthPeriod.query.filter_by(month_code=month_code).first()
    
    if month_period:
        # If found in database, use the defined period
        return month_period.start_date, month_period.end_date
    else:
        # Fallback to standard calendar if not found
        # First day of the month
        start_date = date(year, month, 1)
        
        # Last day of the month
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)
        
        return start_date, end_date

def get_previous_month_days(year, month, num_days=5):
    """Get the last few days of the previous month"""
    year = int(year)
    month = int(month)
    
    first_day = date(year, month, 1)
    
    # Go back 'num_days' days from the first of the month
    previous_days = []
    for i in range(1, num_days + 1):
        day = first_day - timedelta(days=i)
        previous_days.append(day)
    
    # Reverse so they're in chronological order
    return previous_days[::-1]

def generate_timesheet(year, month, department_id=None, custom_start_date=None, custom_end_date=None, housing_id=None):
    """
    Generate timesheet data for the specified month and department/housing
    
    Args:
        year: Year for the timesheet (string or int)
        month: Month for the timesheet (string or int)
        department_id: Optional department ID to filter by
        custom_start_date: Optional custom start date (string in 'YYYY-MM-DD' format)
        custom_end_date: Optional custom end date (string in 'YYYY-MM-DD' format)
        housing_id: Optional housing ID to filter by
        
    Returns:
        Dictionary with timesheet data
    """
    # Import here to avoid circular imports
    from models import Department, Employee, AttendanceRecord, Housing, BiometricTerminal
    from flask import session
    import datetime
    
    try:
        year = int(year)
        month = int(month)
        
        # Use custom dates if provided
        if custom_start_date and custom_end_date:
            try:
                # Parse custom dates
                start_date = datetime.datetime.strptime(custom_start_date, "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(custom_end_date, "%Y-%m-%d").date()
                logger.info(f"Using custom date range: {start_date} to {end_date}")
            except ValueError as e:
                logger.error(f"Error parsing custom dates: {str(e)}")
                # Fall back to default month dates
                start_date, end_date = get_month_start_end_dates(year, month)
        else:
            # Get standard month boundaries
            start_date, end_date = get_month_start_end_dates(year, month)
        
        # Get a few days from previous month for display at start of timesheet
        # (Only if we're not using custom dates)
        if not custom_start_date:
            prev_month_days = get_previous_month_days(year, month, 5)
            
            # Adjust start date to include previous month days
            if prev_month_days:
                start_date = prev_month_days[0]
        
        # Build the list of dates for the timesheet
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Get all employees to include in timesheet (with optional department filter)
        query = Employee.query.filter(Employee.active == True)
        
        if department_id:
            query = query.filter(Employee.department_id == int(department_id))
            
        # Apply Housing filter if provided
        if housing_id:
            query = query.filter(Employee.housing_id == int(housing_id))
        
        employees = query.all()
        
        # إنشاء قاموس لربط أجهزة البصمة بالسكن
        terminal_to_housing = {}
        housing_names = {}  # قاموس لتخزين أسماء السكنات حسب المعرف
        
        # جمع جميع أجهزة البصمة والسكنات المرتبطة بها
        terminals = BiometricTerminal.query.all()
        housings = Housing.query.all()
        
        # تخزين أسماء السكنات حسب المعرف
        for housing in housings:
            housing_names[housing.id] = housing.name
        
        # ربط أجهزة البصمة بالسكن
        for terminal in terminals:
            if terminal.housing_id:
                terminal_to_housing[terminal.terminal_alias] = terminal.housing_id
                # تخزين معرف السكن واسم السكن معاً
                terminal_to_housing[f"{terminal.terminal_alias}_name"] = housing_names.get(terminal.housing_id, "Unknown Housing")
            elif terminal.terminal_alias in terminal_to_housing:
                # إذا كان الجهاز غير مرتبط بسكن محدد لكنه موجود في القاموس (للتوافق مع الإصدارات القديمة)
                terminal_to_housing.pop(terminal.terminal_alias)
        
        # Query all attendance records for these employees in the date range
        attendance_records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id.in_([e.id for e in employees]),
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        ).all()
        
        # Organize attendance records by employee and date
        attendance_by_employee = defaultdict(dict)
        
        # تتبع أجهزة البصمة المستخدمة لكل موظف
        employee_terminals = defaultdict(set)
        
        for record in attendance_records:
            attendance_by_employee[record.employee_id][record.date] = record
            
            # جمع معلومات عن أجهزة البصمة المستخدمة لكل موظف
            if record.terminal_alias_in:
                employee_terminals[record.employee_id].add(record.terminal_alias_in)
            if record.terminal_alias_out:
                employee_terminals[record.employee_id].add(record.terminal_alias_out)
            
        # Get weekend days from user settings
        weekend_days = []
        if 'ui_settings' in session and 'weekend_days' in session['ui_settings']:
            weekend_days = [int(day) for day in session['ui_settings']['weekend_days']]
        else:
            # Default to Friday and Saturday if not set
            weekend_days = [4, 5]  # 4=Friday, 5=Saturday in Python's weekday system (0=Monday)
            
        logger.info(f"Using weekend days: {weekend_days}")
        
        # Build employee rows for the timesheet
        employee_rows = []
        
        for employee in employees:
            attendance_data = []
            
            # For each date in the range, get the attendance status
            for day in dates:
                record = attendance_by_employee.get(employee.id, {}).get(day)
                
                if record:
                    status = record.attendance_status
                else:
                    # If no record, determine if it's a weekend or future date
                    if day.weekday() in weekend_days:  # Using the weekend days from settings
                        status = 'W'  # Weekend
                    elif day > date.today():
                        status = ''  # Future date
                    else:
                        status = 'A'  # Absent
                
                # Add extra information for weekend days
                is_weekend = (day.weekday() in weekend_days)
                
                attendance_data.append({
                    'date': day,
                    'status': status,
                    'record': record,
                    'is_weekend': is_weekend  # Flag for weekend styling
                })
            
            # Get department name
            dept_name = ''
            if employee.department_id:
                dept = Department.query.get(employee.department_id)
                if dept:
                    dept_name = dept.name
                    
            # استخراج معلومات السكن للموظف
            employee_housing_id = employee.housing_id
            housing_name = ''
            
            # إذا كان للموظف سكن محدد، استخدم اسم السكن من قاعدة البيانات
            if employee_housing_id:
                housing = Housing.query.get(employee_housing_id)
                if housing:
                    housing_name = housing.name
            
            # جمع معلومات عن أجهزة البصمة المستخدمة
            devices = employee_terminals.get(employee.id, set())
            terminal_alias_in = None
            
            # إذا لم يكن للموظف سكن محدد، حاول تحديد السكن من أجهزة البصمة
            if not employee_housing_id and devices:
                # محاولة العثور على أول جهاز بصمة مرتبط بسكن
                for device in sorted(devices):  # ترتيب الأجهزة أبجدياً للحصول على نتائج متسقة
                    if device in terminal_to_housing:
                        employee_housing_id = terminal_to_housing[device]
                        housing_name = terminal_to_housing.get(f"{device}_name", "")
                        break
            
            # استخدام أول جهاز بصمة كجهاز افتراضي للموظف إذا كان موجوداً
            if devices:
                terminal_alias_in = sorted(devices)[0]  # استخدام أول جهاز بالترتيب الأبجدي
            
            # إذا لم يتم تحديد سكن للموظف حتى الآن، ضعه في "Unknown Housing"
            if not housing_name:
                housing_name = "Unknown Housing"
            
            # حساب إجمالي ساعات العمل والساعات الإضافية
            total_work_hours = 0
            total_overtime_hours = 0
            
            for day_data in attendance_data:
                record = day_data.get('record')
                if record:
                    total_work_hours += record.work_hours or 0
                    total_overtime_hours += record.overtime_hours or 0
            
            employee_rows.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'name_ar': employee.name_ar,
                'profession': employee.profession,
                'department': dept_name,
                'housing': housing_name,  # اسم السكن
                'housing_id': employee_housing_id,  # معرف السكن
                'attendance': attendance_data,
                'terminal_alias_in': terminal_alias_in,  # جهاز البصمة الأساسي
                'devices': list(devices),  # قائمة بجميع أجهزة البصمة المستخدمة
                'total_work_hours': total_work_hours,  # إجمالي ساعات العمل
                'total_overtime_hours': total_overtime_hours  # إجمالي الساعات الإضافية
            })
        
        # ترتيب الموظفين حسب السكن ثم حسب الاسم
        employee_rows.sort(key=lambda x: (x.get('housing') or 'Unknown Housing', x.get('name') or ''))
        
        # Get month period data if available
        from models import MonthPeriod
        month_code = f"{int(month):02d}/{str(int(year))[2:4]}"
        month_period = MonthPeriod.query.filter_by(month_code=month_code).first()
        
        working_days = None
        working_hours = None
        
        if month_period:
            working_days = month_period.days_in_month
            working_hours = month_period.hours_in_month
            
        # تنظيم الموظفين حسب السكن
        housing_groups = {}
        ungrouped_employees = []
        
        for employee in employee_rows:
            housing_name = employee.get('housing')
            if housing_name:
                if housing_name not in housing_groups:
                    housing_groups[housing_name] = []
                housing_groups[housing_name].append(employee)
            else:
                ungrouped_employees.append(employee)
                
        # بناء قائمة الموظفين النهائية المرتبة حسب السكن
        grouped_employees = []
        
        # أولاً إضافة الموظفين المجمعين حسب السكن
        for housing_name in sorted(housing_groups.keys()):
            grouped_employees.extend(housing_groups[housing_name])
            
        # ثم إضافة الموظفين الذين ليس لديهم سكن
        grouped_employees.extend(ungrouped_employees)
            
        # Build and return timesheet data
        timesheet_data = {
            'year': year,
            'month': month,
            'month_name': get_month_name(month),
            'dates': dates,
            'employees': grouped_employees,  # استخدام القائمة المجمعة حسب السكن
            'total_employees': len(employee_rows),
            'housing_groups': housing_groups,  # تضمين معلومات التجميع حسب السكن
            'start_date': start_date,
            'end_date': end_date,
            'working_days': working_days,
            'working_hours': working_hours,
            'weekend_days': weekend_days  # Include weekend days for reference
        }
        
        return timesheet_data
    
    except Exception as e:
        logger.error(f"Error generating timesheet: {str(e)}")
        # Return empty timesheet structure
        return {
            'year': year,
            'month': month,
            'month_name': get_month_name(int(month)) if isinstance(month, (int, str)) else '',
            'dates': [],
            'employees': [],
            'total_employees': 0,
            'start_date': None,
            'end_date': None,
            'working_days': None,
            'working_hours': None,
            'error': str(e)
        }

def get_department_stats():
    """Get statistics by department for dashboard"""
    # Import here to avoid circular imports
    from models import Department, Employee, AttendanceRecord
    
    try:
        stats = []
        departments = Department.query.all()
        
        for dept in departments:
            # Count employees in department
            employee_count = Employee.query.filter_by(department_id=dept.id, active=True).count()
            
            # Get recent attendance stats (last 7 days)
            today = date.today()
            week_ago = today - timedelta(days=7)
            
            employees_in_dept = Employee.query.filter_by(department_id=dept.id, active=True).all()
            emp_ids = [e.id for e in employees_in_dept]
            
            # Count attendance statuses
            present_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'P'
            ).count()
            
            absent_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'A'
            ).count()
            
            vacation_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'V'
            ).count()
            
            stats.append({
                'id': dept.id,
                'name': dept.name,
                'employee_count': employee_count,
                'present_count': present_count,
                'absent_count': absent_count,
                'vacation_count': vacation_count
            })
            
        return stats
    
    except Exception as e:
        logger.error(f"Error getting department stats: {str(e)}")
        return []

def get_housing_stats():
    """Get statistics by housing for dashboard"""
    # Import here to avoid circular imports
    from models import Housing, Employee, AttendanceRecord
    
    try:
        stats = []
        housings = Housing.query.all()
        
        for housing in housings:
            # Count employees in housing
            employee_count = Employee.query.filter_by(housing_id=housing.id, active=True).count()
            
            # Get recent attendance stats (last 7 days)
            today = date.today()
            week_ago = today - timedelta(days=7)
            
            employees_in_housing = Employee.query.filter_by(housing_id=housing.id, active=True).all()
            emp_ids = [e.id for e in employees_in_housing]
            
            # Count attendance statuses
            present_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'P'
            ).count()
            
            absent_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'A'
            ).count()
            
            vacation_count = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.date >= week_ago,
                AttendanceRecord.date <= today,
                AttendanceRecord.attendance_status == 'V'
            ).count()
            
            stats.append({
                'id': housing.id,
                'name': housing.name,
                'location': housing.location,
                'employee_count': employee_count,
                'present_count': present_count,
                'absent_count': absent_count,
                'vacation_count': vacation_count
            })
            
        return stats
    
    except Exception as e:
        logger.error(f"Error getting housing stats: {str(e)}")
        return []
