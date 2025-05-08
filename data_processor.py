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

def apply_vacations_and_transfers(attendance_data, employee_id, start_date, end_date):
    """
    Apply vacation and transfer statuses to employee attendance data - Optimized with caching
    
    Args:
        attendance_data: List of attendance data dictionaries
        employee_id: Employee ID
        start_date: Start date for the timesheet
        end_date: End date for the timesheet
    
    Returns:
        Updated attendance data with vacation and transfer statuses
    """
    # Import cache manager
    from cache_manager import get_employee_vacations, get_employee_transfers
    
    # Get vacations and transfers using cache
    vacations = get_employee_vacations(employee_id, start_date, end_date)
    transfers = get_employee_transfers(employee_id, start_date, end_date)
    
    # Apply vacation statuses - process by date ranges rather than generating all dates
    for vacation in vacations:
        v_start = max(vacation.start_date, start_date)
        v_end = min(vacation.end_date, end_date)
        
        # Find applicable dates in the attendance data that fall within this vacation
        for day_data in attendance_data:
            day_date = day_data['date']
            if v_start <= day_date <= v_end and (day_data['status'] == 'A' or not day_data['status']):
                day_data['status'] = 'V'
    
    # Apply transfer statuses
    for transfer in transfers:
        t_start = max(transfer.start_date, start_date)
        t_end = min(transfer.end_date, end_date)
        
        # Find applicable dates in the attendance data that fall within this transfer
        for day_data in attendance_data:
            day_date = day_data['date']
            if t_start <= day_date <= t_end:
                day_data['status'] = 'T'
    
    return attendance_data

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
        
        # تتبع السكنات المختلفة المستخدمة من قبل الموظفين في الأيام المختلفة
        employee_daily_housing = defaultdict(lambda: defaultdict(set))
        
        for record in attendance_records:
            attendance_by_employee[record.employee_id][record.date] = record
            
            # جمع معلومات عن أجهزة البصمة المستخدمة لكل موظف
            # وتطبيق القاعدة 1 و 2: إذا تطابقت أجهزة بصمة الدخول والخروج أو اختلفت، نعطي الأولوية لبصمة الدخول
            housing_id_in = None
            housing_id_out = None
            
            if record.terminal_alias_in and record.terminal_alias_in in terminal_to_housing:
                employee_terminals[record.employee_id].add(record.terminal_alias_in)
                housing_id_in = terminal_to_housing[record.terminal_alias_in]
                # أضف السكن المرتبط ببصمة الدخول إلى مجموعة السكنات لهذا اليوم
                if housing_id_in:
                    employee_daily_housing[record.employee_id][record.date].add(housing_id_in)
                
            if record.terminal_alias_out and record.terminal_alias_out in terminal_to_housing:
                employee_terminals[record.employee_id].add(record.terminal_alias_out)
                housing_id_out = terminal_to_housing[record.terminal_alias_out]
                # أضف السكن المرتبط ببصمة الخروج إلى مجموعة السكنات لهذا اليوم فقط إذا كان مختلفًا
                if housing_id_out and housing_id_out != housing_id_in:
                    employee_daily_housing[record.employee_id][record.date].add(housing_id_out)
            
        # Get weekend days from user settings
        weekend_days = []
        if 'ui_settings' in session and 'weekend_days' in session['ui_settings']:
            weekend_days = [int(day) for day in session['ui_settings']['weekend_days']]
        else:
            # Default to Friday and Saturday if not set
            weekend_days = [4, 5]  # 4=Friday, 5=Saturday in Python's weekday system (0=Monday)
            
        logger.info(f"Using weekend days: {weekend_days}")
        
        # قائمة لتخزين جميع صفوف الموظفين، بما في ذلك الموظفين المكررين بسكنات مختلفة
        all_employee_rows = []
        
        # تتبع الموظفين الذين تمت إضافتهم بالفعل إلى صفوف الموظفين
        processed_employee_ids = set()
        
        for employee in employees:
            attendance_data = []
            
            # تتبع جميع السكنات التي استخدمها الموظف خلال الفترة
            all_housing_used = set()
              # For each date in the range, get the attendance status
            for day in dates:
                record = attendance_by_employee.get(employee.id, {}).get(day)
                
                if record:
                    status = record.attendance_status
                    
                    # جمع السكنات المستخدمة في هذا اليوم
                    daily_housings = employee_daily_housing[employee.id].get(day, set())
                    if daily_housings:
                        all_housing_used.update(daily_housings)
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
              # Apply vacations and transfers to attendance data
            attendance_data = apply_vacations_and_transfers(attendance_data, employee.id, start_date, end_date)
            
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
                    # أضف سكن الموظف إلى قائمة السكنات المستخدمة
                    all_housing_used.add(employee_housing_id)
            
            # جمع معلومات عن أجهزة البصمة المستخدمة
            devices = employee_terminals.get(employee.id, set())
            terminal_alias_in = None
            
            # إذا لم يكن للموظف سكن محدد، حاول تحديد السكن من أجهزة البصمة المستخدمة بتطبيق القواعد
            if not employee_housing_id and devices:
                # Count terminal usage by housing
                housing_usage = defaultdict(int)
                
                # محاولة تحديد السكن بناءً على تكرار استخدام الأجهزة
                for device in devices:
                    if device in terminal_to_housing:
                        housing_id = terminal_to_housing[device]
                        housing_usage[housing_id] += 1
                
                # If we have housing usage data, use the most frequent one
                if housing_usage:
                    most_used_housing_id = max(housing_usage.items(), key=lambda x: x[1])[0]
                    employee_housing_id = most_used_housing_id
                    housing_name = housing_names.get(most_used_housing_id, "")
                    # أضف السكن الأكثر استخدامًا إلى قائمة السكنات المستخدمة
                    all_housing_used.add(most_used_housing_id)
            
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
                    # حساب ساعات العمل العادية (بحد أقصى 8 ساعات في اليوم) والساعات الإضافية
                    total_hours = record.work_hours + record.overtime_hours
                    regular_hours = min(8, total_hours)  # ساعات العمل العادية بحد أقصى 8 ساعات
                    overtime = total_hours - regular_hours if total_hours > 8 else 0  # الساعات الإضافية فوق ال 8 ساعات
                    
                    total_work_hours += regular_hours
                    total_overtime_hours += overtime
            
            # إضافة الموظف بالسكن الرئيسي أولاً
            all_employee_rows.append({
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
                'total_overtime_hours': total_overtime_hours,  # إجمالي الساعات الإضافية
                'is_primary': True  # علامة للإشارة إلى أنه السكن الرئيسي للموظف
            })
            
            # إضافة الموظف إلى قائمة المعالجة
            processed_employee_ids.add(employee.id)
            
            # قاعدة 3: إظهار الموظف في السكنات الأخرى التي بصم فيها
            # إنشاء نسخة من الموظف لكل سكن إضافي استخدمه
            for housing_id in all_housing_used:
                # تخطي السكن الرئيسي الذي تمت إضافته بالفعل
                if housing_id == employee_housing_id:
                    continue
                
                # الحصول على اسم السكن
                secondary_housing_name = housing_names.get(housing_id, "Unknown Housing")
                
                # إنشاء نسخة من بيانات الموظف مع تحديد السكن الثانوي
                all_employee_rows.append({
                    'id': employee.id,
                    'emp_code': employee.emp_code,
                    'name': employee.name,
                    'name_ar': employee.name_ar,
                    'profession': employee.profession,
                    'department': dept_name,
                    'housing': secondary_housing_name,  # اسم السكن الثانوي
                    'housing_id': housing_id,  # معرف السكن الثانوي
                    'attendance': attendance_data,
                    'terminal_alias_in': terminal_alias_in,  # جهاز البصمة الأساسي
                    'devices': list(devices),  # قائمة بجميع أجهزة البصمة المستخدمة
                    'total_work_hours': total_work_hours,  # إجمالي ساعات العمل
                    'total_overtime_hours': total_overtime_hours,  # إجمالي الساعات الإضافية
                    'is_primary': False  # علامة للإشارة إلى أنه سكن ثانوي للموظف
                })
        
        # استخدام القائمة الجديدة التي تتضمن الموظفين المكررين بالسكنات المختلفة
        employee_rows = all_employee_rows
        
        # ترتيب الموظفين حسب السكن ثم حسب الاسم
        employee_rows.sort(key=lambda x: (x.get('housing') or 'Unknown Housing', x.get('name') or '', not x.get('is_primary', False)))
        
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
            'total_employees': len(employees),  # عدد الموظفين الفريدين (بدون التكرار)
            'total_rows': len(employee_rows),  # العدد الإجمالي للصفوف بما فيها المكررة
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

def update_employee_housing_from_terminals():
    """
    Update employee housing assignments based on their biometric terminal usage patterns.
    This function analyzes all attendance records and updates employee housing assignments
    based on the following rules:
    1. If check-in and check-out terminals match for a day, use that terminal's housing
    2. If check-in and check-out terminals differ, prioritize the check-in terminal
    
    Improved version:
    - Looks back 60 days instead of 30 
    - Reduces minimum terminal usage to 2 instead of 3
    - Filters out common terminals that don't represent housing locations
    - Improved logging for better troubleshooting
    """
    # Import here to avoid circular imports
    from models import Employee, AttendanceRecord, BiometricTerminal, Housing
    from database import db
    import logging
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    try:
        logger = logging.getLogger(__name__)
        logger.info("Starting improved automatic housing assignment based on terminal usage")
        
        # Get all active employees without housing assignments
        employees_without_housing = Employee.query.filter(
            Employee.active == True,
            (Employee.housing_id == None) | (Employee.housing_id == 0)
        ).all()
        
        logger.info(f"Found {len(employees_without_housing)} active employees without housing assignments")
        
        # Get the mapping of terminals to housing
        terminal_to_housing = {}
        terminals = BiometricTerminal.query.filter(BiometricTerminal.housing_id != None).all()
          # Common terminals that don't represent housing (security checkpoints and office locations)
        common_terminals = [
            "SECURITY-oldwoodcamp",
            "SECURITY-oldgypcamp",
            "HeadOffice1",
            "HeadOffice2",
            "SECURITY-MAIN",
            "SECURITY-GATE", 
            "SECURITY-B",
            "SECURITY-C",
            "SECURITY"
        ]
        
        terminal_count = 0
        for terminal in terminals:
            if terminal.terminal_alias not in common_terminals:
                terminal_to_housing[terminal.terminal_alias] = terminal.housing_id
                terminal_count += 1
        
        logger.info(f"Loaded {terminal_count} biometric terminals mapped to housing locations")
        
        # Check recent attendance records (last 60 days for more data points)
        today = datetime.now().date()
        two_months_ago = today - timedelta(days=60)
        
        logger.info(f"Analyzing attendance records from {two_months_ago} to {today}")
        
        # Process each employee without housing
        updated_count = 0
        no_records_count = 0
        insufficient_usage_count = 0
        
        for employee in employees_without_housing:
            # Get employee's attendance records for the last two months
            records = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id == employee.id,
                AttendanceRecord.date >= two_months_ago
            ).order_by(AttendanceRecord.date.desc()).all()
            
            if not records:
                no_records_count += 1
                continue
                
            # Group records by date to analyze daily terminal usage
            records_by_date = defaultdict(list)
            for record in records:
                records_by_date[record.date].append(record)
                
            # Count terminal usage by housing with priority rules
            housing_usage = defaultdict(int)
            check_in_terminals_used = set()
            
            # Apply the rules for each day's attendance records
            for date, day_records in records_by_date.items():
                # Keep track of which terminals were used for check-in on this date
                # to avoid double counting if an employee has multiple check-ins at the same terminal
                daily_housing_counted = set()
                
                for record in day_records:
                    # Rule 1 & 2: If check-in and check-out terminals match or differ, prioritize check-in
                    if record.terminal_alias_in and record.terminal_alias_in in terminal_to_housing:
                        # Always prioritize the check-in terminal
                        housing_id = terminal_to_housing[record.terminal_alias_in]
                        
                        # Only count once per day for the same housing
                        if housing_id not in daily_housing_counted:
                            housing_usage[housing_id] += 1
                            daily_housing_counted.add(housing_id)
                            
                        check_in_terminals_used.add(record.terminal_alias_in)
                        
                    # Only consider check-out terminal if it's different & we don't have a check-in terminal
                    elif record.terminal_alias_out and record.terminal_alias_out in terminal_to_housing:
                        housing_id = terminal_to_housing[record.terminal_alias_out]
                        
                        # Only count once per day for the same housing
                        if housing_id not in daily_housing_counted:
                            housing_usage[housing_id] += 1
                            daily_housing_counted.add(housing_id)
            
            # If employee has used terminals, assign to most frequently used housing
            if housing_usage:
                # Find the housing with maximum usage
                sorted_usage = sorted(housing_usage.items(), key=lambda x: x[1], reverse=True)
                most_used_housing_id = sorted_usage[0][0]
                usage_count = sorted_usage[0][1]
                
                # Log the terminals this employee used for check-in
                logger.info(f"Employee {employee.emp_code} ({employee.name}) used terminals: {', '.join(check_in_terminals_used)}")
                logger.info(f"Housing usage counts: {dict(sorted_usage)}")
                
                # Update employee's housing if they used this housing's terminals at least 2 times
                # (reduced from 3 to catch more employees)
                if usage_count >= 2:
                    housing = Housing.query.get(most_used_housing_id)
                    if housing:
                        employee.housing_id = most_used_housing_id
                        updated_count += 1
                        logger.info(f"Updated employee {employee.emp_code} ({employee.name}) housing to {housing.name} based on {usage_count} terminal usages")
                else:
                    insufficient_usage_count += 1
                    logger.info(f"Employee {employee.emp_code} doesn't have enough terminal usage (only {usage_count})")
            else:
                logger.info(f"No housing-connected terminals found for employee {employee.emp_code}")
        
        # Save all changes
        if updated_count > 0:
            db.session.commit()
            logger.info(f"Updated housing for {updated_count} employees")
            logger.info(f"Employees with no records: {no_records_count}")
            logger.info(f"Employees with insufficient terminal usage: {insufficient_usage_count}")
        else:
            logger.info(f"No employees needed housing updates. {no_records_count} had no records and {insufficient_usage_count} had insufficient usage.")
            
        return updated_count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating employee housing: {str(e)}")
        return 0
