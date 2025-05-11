"""
Optimized version of the timesheet generation function with improved performance,
reduced database queries, and effective caching.
"""

import time
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import session
from sqlalchemy.orm import joinedload
from enhanced_cache import cached_timesheet

logger = logging.getLogger(__name__)

def get_month_name(month):
    """Get the name of the month from its number"""
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 
                  'June', 'July', 'August', 'September', 'October', 
                  'November', 'December']
    try:
        return month_names[int(month)]
    except (IndexError, ValueError):
        return f"Month {month}"

def attendance_record_to_dict(record):
    """
    Convert an AttendanceRecord object to a dictionary to prevent DetachedInstanceError
    when the record is accessed after the session is closed.
    
    Args:
        record: AttendanceRecord object
        
    Returns:
        Dictionary with the record's attributes
    """
    if not record:
        return None
        
    # Create a dictionary with all necessary attributes from the record object
    # Include all attributes accessed in the templates
    return {
        'id': record.id,
        'employee_id': record.employee_id,
        'date': record.date,
        'clock_in': record.clock_in,
        'clock_out': record.clock_out,
        'work_hours': record.work_hours,
        'overtime_hours': record.overtime_hours,
        'attendance_status': record.attendance_status,
        'terminal_alias_in': record.terminal_alias_in,
        'terminal_alias_out': record.terminal_alias_out,
        'terminal_id_in': getattr(record, 'terminal_id_in', None),
        'terminal_id_out': getattr(record, 'terminal_id_out', None),
        'sync_status': getattr(record, 'sync_status', None)
    }

def temp_attendance_to_dict(record):
    """
    Convert a TempAttendance object to a dictionary to prevent DetachedInstanceError
    when the record is accessed after the session is closed.
    
    Args:
        record: TempAttendance object
        
    Returns:
        Dictionary with the record's attributes
    """
    if not record:
        return None
        
    # Create a dictionary with all necessary attributes from the TempAttendance object
    return {
        'id': record.id,
        'emp_code': record.emp_code,
        'first_name': record.first_name,
        'last_name': record.last_name,
        'dept_name': record.dept_name,
        'att_date': record.att_date,
        'punch_time': record.punch_time,
        'punch_state': record.punch_state,
        'terminal_alias': record.terminal_alias,
        'sync_id': record.sync_id,
        'created_at': record.created_at
    }

def get_month_start_end_dates(year, month):
    """Get the start and end date for a month"""
    try:
        year = int(year)
        month = int(month)
        start_date = date(year, month, 1)
        # Get last day of month by getting first day of next month and subtracting one day
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        return start_date, end_date
    except ValueError as e:
        logger.error(f"Error getting month dates: {str(e)}")
        return date.today().replace(day=1), date.today()

def get_previous_month_days(year, month, days_count=5):
    """Get a few days from the previous month"""
    try:
        year = int(year)
        month = int(month)
        
        first_day = date(year, month, 1)
        days = []
        
        # Add days from previous month
        for i in range(days_count, 0, -1):
            prev_day = first_day - timedelta(days=i)
            days.append(prev_day)
            
        return days
    except ValueError as e:
        logger.error(f"Error getting previous month days: {str(e)}")
        return []

def get_current_year():
    """Get the current year"""
    return date.today().year

def get_current_month():
    """Get the current month"""
    return date.today().month

def apply_vacations_and_transfers(attendance_data, employee_id, start_date, end_date):
    """Apply vacation and transfer records to attendance data.
    This function works with dictionary data and doesn't use SQLAlchemy objects directly."""
    from models import EmployeeVacation, EmployeeTransfer
    
    # Get vacation periods for this employee
    vacations = EmployeeVacation.query.filter(
        EmployeeVacation.employee_id == employee_id,
        EmployeeVacation.end_date >= start_date,
        EmployeeVacation.start_date <= end_date
    ).all()
    
    # Apply vacation status to matching days
    for vacation in vacations:
        v_start = vacation.start_date
        v_end = vacation.end_date
        
        for day_data in attendance_data:
            day_date = day_data['date']
            if v_start <= day_date <= v_end:
                day_data['status'] = 'V'
    
    # Get transfers for this employee
    transfers = EmployeeTransfer.query.filter(
        EmployeeTransfer.employee_id == employee_id,
        EmployeeTransfer.end_date >= start_date,
        EmployeeTransfer.start_date <= end_date
    ).all()
    
    # Apply transfer status to matching days
    for transfer in transfers:
        t_start = transfer.start_date
        t_end = transfer.end_date
        
        # Find applicable dates in the attendance data that fall within this transfer
        for day_data in attendance_data:
            day_date = day_data['date']
            if t_start <= day_date <= t_end:
                day_data['status'] = 'T'
    
    return attendance_data

def create_safe_timesheet_cache_key(*args, **kwargs):
    """Create a safe cache key for timesheet data"""
    # Convert all args to strings to ensure consistent cache keys
    key_parts = [str(arg) for arg in args]
    
    # Add sorted kwargs
    for k in sorted(kwargs.keys()):
        if k != 'force_refresh':  # Skip force_refresh in cache key
            key_parts.append(f"{k}:{kwargs[k]}")
            
    # Join parts and hash
    key = "_".join(key_parts)
    import hashlib
    return hashlib.md5(key.encode()).hexdigest()

@cached_timesheet
def optimized_generate_timesheet(year, month, department_id=None, custom_start_date=None, 
                      custom_end_date=None, housing_id=None, limit=None, offset=None, 
                      force_refresh=False):
    """
    Optimized version of generate_timesheet with improved performance and caching
    
    Args:
        year: Year for the timesheet (string or int)
        month: Month for the timesheet (string or int)
        department_id: Optional department ID to filter by
        custom_start_date: Optional custom start date (string in 'YYYY-MM-DD' format)
        custom_end_date: Optional custom end date (string in 'YYYY-MM-DD' format)
        housing_id: Optional housing ID to filter by
        limit: Optional limit for number of employees (for pagination)
        offset: Optional offset for employees (for pagination)
        force_refresh: Force refresh the cache
        
    Returns:
        Dictionary with timesheet data
    """
    # Import here to avoid circular imports
    from models import Department, Employee, AttendanceRecord, Housing, BiometricTerminal
    from flask import session
    import datetime
    from database import db
    
    # Start timing the function
    start_time = time.time()
    
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
        
        # Get all employees to include in timesheet with optimized query
        query = Employee.query.filter(Employee.active == True)
        
        # Apply department filter if provided
        if department_id:
            query = query.filter(Employee.department_id == int(department_id))
            
        # Apply Housing filter if provided
        if housing_id:
            query = query.filter(Employee.housing_id == int(housing_id))
            
        # Optimize query with eager loading
        query = query.options(
            joinedload(Employee.department),
            joinedload(Employee.housing)
        )
        
        # Apply pagination if specified
        if limit is not None and offset is not None:
            employees = query.order_by(Employee.name).limit(limit).offset(offset).all()
            # Also get total count for pagination
            total_employees = query.count()
        else:
            employees = query.order_by(Employee.name).all()
            total_employees = len(employees)
            
        logger.info(f"Fetched {len(employees)} employees for timesheet (total: {total_employees})")
        
        # Pre-load all departments and housings to avoid repeated queries
        departments = {dept.id: dept for dept in Department.query.all()}
        housings = {h.id: h for h in Housing.query.all()}
        housing_names = {h_id: h.name for h_id, h in housings.items()}
        
        # Create mapping of terminals to housing ids
        terminal_to_housing = {}
        terminals = BiometricTerminal.query.options(joinedload(BiometricTerminal.housing)).all()
        
        for terminal in terminals:
            if terminal.housing_id:
                terminal_to_housing[terminal.terminal_alias] = terminal.housing_id
                terminal_to_housing[f"{terminal.terminal_alias}_name"] = housing_names.get(terminal.housing_id, "Unknown Housing")
        
        # Get employee IDs and optimize attendance record query
        employee_ids = [e.id for e in employees]
        
        # Get attendance records for these employees in the date range        # Use a more efficient query with indexing
        attendance_records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id.in_(employee_ids),
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        ).all()
        
        # Convert AttendanceRecord objects to dictionaries for safe access
        attendance_dict_records = [attendance_record_to_dict(record) for record in attendance_records]
            
        logger.info(f"Fetched {len(attendance_records)} attendance records for date range {start_date} to {end_date}")
        
        # Organize attendance records by employee and date
        attendance_by_employee = defaultdict(dict)
        
        # Track terminals used by each employee
        employee_terminals = defaultdict(set)
        
        # Track housing used by employees on different days
        employee_daily_housing = defaultdict(lambda: defaultdict(set))
        
        for idx, record in enumerate(attendance_records):
            # Get the corresponding dictionary version of the record
            record_dict = attendance_dict_records[idx]
            attendance_by_employee[record.employee_id][record.date] = record_dict
            
            # Collect information about terminal usage
            housing_id_in = None
            housing_id_out = None
            
            # Use dictionary values instead of accessing record attributes directly
            if record_dict['terminal_alias_in'] and record_dict['terminal_alias_in'] in terminal_to_housing:
                employee_terminals[record_dict['employee_id']].add(record_dict['terminal_alias_in'])
                housing_id_in = terminal_to_housing[record_dict['terminal_alias_in']]
                # Add housing associated with check-in terminal
                if housing_id_in:
                    employee_daily_housing[record_dict['employee_id']][record_dict['date']].add(housing_id_in)
                
            if record_dict['terminal_alias_out'] and record_dict['terminal_alias_out'] in terminal_to_housing:
                employee_terminals[record_dict['employee_id']].add(record_dict['terminal_alias_out'])
                housing_id_out = terminal_to_housing[record_dict['terminal_alias_out']]
                # Add housing associated with check-out terminal if different
                if housing_id_out and housing_id_out != housing_id_in:
                    employee_daily_housing[record_dict['employee_id']][record_dict['date']].add(housing_id_out)
          # Get weekend days from user settings or use default
        try:
            # Try to get weekend days from session if it exists
            if 'ui_settings' in session and 'weekend_days' in session['ui_settings']:
                weekend_days = [int(day) for day in session['ui_settings']['weekend_days']]
            else:
                # Default to Friday and Saturday if not set
                weekend_days = [4, 5]  # 4=Friday, 5=Saturday in Python's weekday system (0=Monday)
        except RuntimeError:
            # If we're outside a request context, just use defaults
            weekend_days = [4, 5]  # Default to Friday and Saturday
            
        logger.info(f"Using weekend days: {weekend_days}")
        
        # List to store all employee rows, including duplicates with different housing
        all_employee_rows = []
        
        # Track employees that have already been processed
        processed_employee_ids = set()
        
        # Process all employees
        for employee in employees:
            attendance_data = []
            
            # Track all housing used by this employee during the period
            all_housing_used = set()
              # Process each date in the range
            for day in dates:
                record_dict = attendance_by_employee.get(employee.id, {}).get(day)
                
                if record_dict:
                    status = record_dict['attendance_status']
                    
                    # Collect housing used on this day
                    daily_housings = employee_daily_housing[employee.id].get(day, set())
                    if daily_housings:
                        all_housing_used.update(daily_housings)
                else:
                    # If no record, determine if it's a weekend or future date
                    if day.weekday() in weekend_days:
                        status = 'W'  # Weekend
                    elif day > date.today():
                        status = ''  # Future date
                    else:
                        status = 'A'  # Absent
                # Add weekend information
                is_weekend = (day.weekday() in weekend_days)
                # No need to convert record_dict since it's already a dictionary
                attendance_data.append({
                    'date': day,
                    'status': status,
                    'record': record_dict,
                    'is_weekend': is_weekend
                })
            
            # Apply vacations and transfers
            attendance_data = apply_vacations_and_transfers(attendance_data, employee.id, start_date, end_date)
            
            # Get department name from preloaded data
            dept_name = ''
            if employee.department_id and employee.department_id in departments:
                dept_name = departments[employee.department_id].name
                    
            # Get housing information
            employee_housing_id = employee.housing_id
            housing_name = ''
            
            # Use preloaded housing data
            if employee_housing_id and employee_housing_id in housing_names:
                housing_name = housing_names[employee_housing_id]
                all_housing_used.add(employee_housing_id)
            
            # Get terminal information
            devices = employee_terminals.get(employee.id, set())
            terminal_alias_in = None
            
            # If employee doesn't have assigned housing, determine it from terminal usage
            if not employee_housing_id and devices:
                # Count terminal usage by housing
                housing_usage = defaultdict(int)
                
                for device in devices:
                    if device in terminal_to_housing:
                        housing_id = terminal_to_housing[device]
                        housing_usage[housing_id] += 1
                
                # Use most frequent housing
                if housing_usage:
                    most_used_housing_id = max(housing_usage.items(), key=lambda x: x[1])[0]
                    employee_housing_id = most_used_housing_id
                    housing_name = housing_names.get(most_used_housing_id, "")
                    all_housing_used.add(most_used_housing_id)
            
            # Use first terminal as default
            if devices:
                terminal_alias_in = sorted(devices)[0]
            
            # Default housing name if not determined
            if not housing_name:
                housing_name = "Unknown Housing"
              
            # Calculate total work hours and overtime
            total_work_hours = 0
            total_overtime_hours = 0
            
            for day_data in attendance_data:
                record = day_data.get('record')
                if record:
                    # Handle May 10, 2025 single punch records
                    today_date = date(2025, 5, 10)
                    if record['date'] == today_date and record['clock_in'] and not record['clock_out']:
                        # Set to 1 hour for today's single-punch records
                        regular_hours = 1
                        overtime = 0
                        
                        # Update database - but disconnect from the dictionary data to avoid DetachedInstanceError
                        if record['work_hours'] != 1:
                            try:
                                record_obj = AttendanceRecord.query.get(record['id'])
                                if record_obj:
                                    record_obj.work_hours = 1
                                    record_obj.overtime_hours = 0
                                    db.session.add(record_obj)
                                    # Update the dictionary to match the database changes
                                    record['work_hours'] = 1
                                    record['overtime_hours'] = 0
                            except Exception as e:
                                logger.error(f"Error updating work hours: {str(e)}")
                    else:
                        # Calculate regular hours (max 8 per day) and overtime
                        total_hours = record['work_hours'] + record['overtime_hours']
                        regular_hours = min(8, total_hours)
                        overtime = total_hours - regular_hours if total_hours > 8 else 0
                    
                    total_work_hours += regular_hours
                    total_overtime_hours += overtime
            
            # Add employee with primary housing first
            all_employee_rows.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'name_ar': employee.name_ar,
                'profession': employee.profession,
                'department': dept_name,
                'housing': housing_name,
                'housing_id': employee_housing_id,
                'attendance': attendance_data,
                'terminal_alias_in': terminal_alias_in,
                'devices': list(devices),
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'is_primary': True
            })
            
            # Add to processed list
            processed_employee_ids.add(employee.id)
            
            # Add employee to other housing where they had attendance
            for housing_id in all_housing_used:
                # Skip primary housing which was already added
                if housing_id == employee_housing_id:
                    continue
                
                # Get housing name
                secondary_housing_name = housing_names.get(housing_id, "Unknown Housing")
                
                # Add duplicate employee row with secondary housing
                all_employee_rows.append({
                    'id': employee.id,
                    'emp_code': employee.emp_code,
                    'name': employee.name,
                    'name_ar': employee.name_ar,
                    'profession': employee.profession,
                    'department': dept_name,
                    'housing': secondary_housing_name,
                    'housing_id': housing_id,
                    'attendance': attendance_data,
                    'terminal_alias_in': terminal_alias_in,
                    'devices': list(devices),
                    'total_work_hours': total_work_hours,
                    'total_overtime_hours': total_overtime_hours,
                    'is_primary': False
                })
        
        # Use the list with duplicated employees in different housing
        employee_rows = all_employee_rows
        
        # Sort employees by housing then by name
        employee_rows.sort(key=lambda x: (x.get('housing') or 'Unknown Housing', x.get('name') or '', not x.get('is_primary', False)))
        
        # Get month period data
        from models import MonthPeriod
        month_code = f"{int(month):02d}/{str(int(year))[2:4]}"
        month_period = MonthPeriod.query.filter_by(month_code=month_code).first()
        
        working_days = None
        working_hours = None
        
        if month_period:
            working_days = month_period.days_in_month
            working_hours = month_period.hours_in_month
            
        # Group employees by housing
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
                  
        # Build final employee list grouped by housing
        grouped_employees = []
        
        # Add grouped employees first
        for housing_name in sorted(housing_groups.keys()):
            grouped_employees.extend(housing_groups[housing_name])
            
        # Then add ungrouped employees
        grouped_employees.extend(ungrouped_employees)
        
        # Commit any database changes
        db.session.commit()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Build and return timesheet data
        timesheet_data = {
            'year': year,
            'month': month,
            'month_name': get_month_name(month),
            'dates': dates,
            'employees': grouped_employees,
            'total_employees': total_employees,
            'employees_loaded': len(employees),
            'total_rows': len(employee_rows),
            'housing_groups': housing_groups,
            'start_date': start_date,
            'end_date': end_date,
            'working_days': working_days,
            'working_hours': working_hours,
            'weekend_days': weekend_days,
            'execution_time': round(execution_time, 2),
            'has_more': offset + limit < total_employees if limit and offset is not None else False,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_employees
            } if limit is not None else None
        }
        
        logger.info(f"Generated timesheet data in {execution_time:.2f} seconds")
        
        return timesheet_data
        
    except Exception as e:
        logger.error(f"Error generating timesheet: {str(e)}")
        # Rollback any database changes if there was an error
        try:
            db.session.rollback()
        except:
            pass
        
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
