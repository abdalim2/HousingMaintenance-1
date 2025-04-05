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

def get_month_days(year, month):
    """Get number of days in month"""
    return calendar.monthrange(int(year), int(month))[1]

def get_month_start_end_dates(year, month):
    """Get start and end dates for a month"""
    year = int(year)
    month = int(month)
    
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

def generate_timesheet(year, month, department_id=None):
    """
    Generate timesheet data for the specified month and department
    
    Args:
        year: Year for the timesheet (string or int)
        month: Month for the timesheet (string or int)
        department_id: Optional department ID to filter by
        
    Returns:
        Dictionary with timesheet data
    """
    # Import here to avoid circular imports
    from models import Department, Employee, AttendanceRecord
    
    try:
        year = int(year)
        month = int(month)
        
        # Get month boundaries
        start_date, end_date = get_month_start_end_dates(year, month)
        
        # Get a few days from previous month for display at start of timesheet
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
        
        employees = query.all()
        
        # Query all attendance records for these employees in the date range
        attendance_records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id.in_([e.id for e in employees]),
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        ).all()
        
        # Organize attendance records by employee and date
        attendance_by_employee = defaultdict(dict)
        for record in attendance_records:
            attendance_by_employee[record.employee_id][record.date] = record
        
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
                    if day.weekday() >= 5:  # Saturday or Sunday
                        status = 'W'  # Weekend
                    elif day > date.today():
                        status = ''  # Future date
                    else:
                        status = 'A'  # Absent
                
                attendance_data.append({
                    'date': day,
                    'status': status,
                    'record': record
                })
            
            # Get department name
            dept_name = ''
            if employee.department_id:
                dept = Department.query.get(employee.department_id)
                if dept:
                    dept_name = dept.name
            
            employee_rows.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'name_ar': employee.name_ar,
                'profession': employee.profession,
                'department': dept_name,
                'attendance': attendance_data
            })
        
        # Build and return timesheet data
        timesheet_data = {
            'year': year,
            'month': month,
            'month_name': get_month_name(month),
            'dates': dates,
            'employees': employee_rows,
            'total_employees': len(employee_rows)
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
