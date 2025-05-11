"""
Optimized data processing module for the Housing Maintenance application.
This module provides improved performance for data processing operations.
"""
import logging
import time
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import func, and_, or_
from flask import current_app, g
from database import db
from translations import get_text
from enhanced_cache_optimized import cached_timesheet, attendance_record_to_dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache for terminal to housing mapping
_terminal_housing_cache = {}
_terminal_housing_timestamp = 0
_terminal_housing_cache_ttl = 1800  # 30 minutes

def get_terminal_to_housing_mapping():
    """Get mapping of terminal aliases to housing IDs with caching"""
    global _terminal_housing_cache, _terminal_housing_timestamp
    
    # Check if cache is valid
    if _terminal_housing_cache and time.time() - _terminal_housing_timestamp < _terminal_housing_cache_ttl:
        return _terminal_housing_cache
    
    # Cache is invalid, refresh it
    from models import BiometricTerminal
    
    terminal_to_housing = {}
    try:
        terminals = BiometricTerminal.query.all()
        for terminal in terminals:
            if terminal.alias:
                terminal_to_housing[terminal.alias] = terminal.housing_id
    except Exception as e:
        logger.error(f"Error getting terminal to housing mapping: {str(e)}")
    
    # Update cache
    _terminal_housing_cache = terminal_to_housing
    _terminal_housing_timestamp = time.time()
    
    return terminal_to_housing

def get_current_month():
    """Get the current month as a string"""
    return str(datetime.now().month)

def get_current_year():
    """Get the current year as a string"""
    return str(datetime.now().year)

def get_month_name(month_number):
    """Get the name of a month by its number"""
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
    
    try:
        month_number = int(month_number)
        if 1 <= month_number <= 12:
            return month_names[month_number]
    except:
        pass
    
    return ''

def apply_vacations_and_transfers(employee_id, attendance_by_date, start_date, end_date):
    """Apply vacation and transfer records to attendance data"""
    from models import EmployeeVacation, EmployeeTransfer
    
    # Get vacation records for this employee in the date range
    vacations = EmployeeVacation.query.filter(
        EmployeeVacation.employee_id == employee_id,
        EmployeeVacation.start_date <= end_date,
        EmployeeVacation.end_date >= start_date
    ).all()
    
    # Get transfer records for this employee in the date range
    transfers = EmployeeTransfer.query.filter(
        EmployeeTransfer.employee_id == employee_id,
        EmployeeTransfer.start_date <= end_date,
        EmployeeTransfer.end_date >= start_date
    ).all()
    
    # Apply vacation records
    for vacation in vacations:
        # Calculate the overlap between vacation and the requested date range
        overlap_start = max(vacation.start_date, start_date)
        overlap_end = min(vacation.end_date, end_date)
        
        # Apply vacation status to each day in the overlap
        current_date = overlap_start
        while current_date <= overlap_end:
            # Only override if there's no existing record or the existing record is absent
            if current_date not in attendance_by_date or attendance_by_date[current_date].get('attendance_status') == 'A':
                attendance_by_date[current_date] = {
                    'attendance_status': 'V',  # Vacation
                    'is_generated': True
                }
            current_date += timedelta(days=1)
    
    # Apply transfer records
    for transfer in transfers:
        # Calculate the overlap between transfer and the requested date range
        overlap_start = max(transfer.start_date, start_date)
        overlap_end = min(transfer.end_date, end_date)
        
        # Apply transfer status to each day in the overlap
        current_date = overlap_start
        while current_date <= overlap_end:
            # Only override if there's no existing record or the existing record is absent
            if current_date not in attendance_by_date or attendance_by_date[current_date].get('attendance_status') == 'A':
                attendance_by_date[current_date] = {
                    'attendance_status': 'T',  # Transfer
                    'is_generated': True,
                    'from_department_id': transfer.from_department_id,
                    'to_department_id': transfer.to_department_id,
                    'from_housing_id': transfer.from_housing_id,
                    'to_housing_id': transfer.to_housing_id
                }
            current_date += timedelta(days=1)
    
    return attendance_by_date

@cached_timesheet
def generate_optimized_timesheet(year, month, department_id=None, custom_start_date=None, 
                      custom_end_date=None, housing_id=None, limit=None, offset=None, 
                      force_refresh=False):
    """
    Generate timesheet data with optimized performance
    """
    from models import Employee, AttendanceRecord, Department, Housing, MonthPeriod
    
    start_time = time.time()
    logger.info(f"Generating timesheet for {year}/{month} (dept={department_id}, housing={housing_id})")
    
    try:
        # Convert parameters to appropriate types
        year = str(year)
        month = str(month)
        
        if department_id:
            department_id = int(department_id)
        
        if housing_id:
            housing_id = int(housing_id)
        
        # Get month period data if available
        month_code = f"{int(month):02d}/{str(int(year))[2:4]}"
        month_period = MonthPeriod.query.filter_by(month_code=month_code).first()
        
        # Determine date range
        if custom_start_date and custom_end_date:
            # Use custom date range if provided
            if isinstance(custom_start_date, str):
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
            else:
                start_date = custom_start_date
                
            if isinstance(custom_end_date, str):
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
            else:
                end_date = custom_end_date
        elif month_period and month_period.start_date and month_period.end_date:
            # Use month period dates if available
            start_date = month_period.start_date
            end_date = month_period.end_date
        else:
            # Use calendar month as fallback
            start_date = date(int(year), int(month), 1)
            # Get the last day of the month
            if int(month) == 12:
                end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
        
        # Generate list of dates in the range
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Get weekend days (default to Friday and Saturday)
        weekend_days = [4, 5]  # 0=Monday, 6=Sunday in Python's datetime.weekday()
        
        # Build employee query
        employee_query = Employee.query.filter(Employee.active == True)
        
        # Apply department filter if specified
        if department_id:
            employee_query = employee_query.filter(Employee.department_id == department_id)
        
        # Apply housing filter if specified
        if housing_id:
            employee_query = employee_query.filter(Employee.housing_id == housing_id)
        
        # Apply pagination if specified
        if limit is not None and offset is not None:
            employees = employee_query.limit(limit).offset(offset).all()
            total_employees = employee_query.count()
        else:
            employees = employee_query.all()
            total_employees = len(employees)
        
        # Get terminal to housing mapping
        terminal_to_housing = get_terminal_to_housing_mapping()
        
        # Prepare data structures for processing
        employee_ids = [e.id for e in employees]
        attendance_records = []
        
        # Process employees in chunks to avoid memory issues with large datasets
        chunk_size = 50
        for i in range(0, len(employee_ids), chunk_size):
            chunk_ids = employee_ids[i:i+chunk_size]
            
            # Get attendance records for this chunk of employees
            chunk_records = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(chunk_ids),
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date
            ).all()
            
            # Convert to dictionaries to prevent DetachedInstanceError
            chunk_records = [attendance_record_to_dict(record) for record in chunk_records]
            attendance_records.extend(chunk_records)
        
        # Process attendance records
        attendance_by_employee = defaultdict(dict)
        employee_terminals = defaultdict(set)
        employee_daily_housing = defaultdict(lambda: defaultdict(set))
        
        for record in attendance_records:
            attendance_by_employee[record['employee_id']][record['date']] = record
            
            # Track terminal usage for housing assignment
            housing_id_in = None
            if record['terminal_alias_in'] and record['terminal_alias_in'] in terminal_to_housing:
                employee_terminals[record['employee_id']].add(record['terminal_alias_in'])
                housing_id_in = terminal_to_housing[record['terminal_alias_in']]
                if housing_id_in:
                    employee_daily_housing[record['employee_id']][record['date']].add(housing_id_in)
            
            housing_id_out = None
            if record['terminal_alias_out'] and record['terminal_alias_out'] in terminal_to_housing:
                employee_terminals[record['employee_id']].add(record['terminal_alias_out'])
                housing_id_out = terminal_to_housing[record['terminal_alias_out']]
                if housing_id_out:
                    employee_daily_housing[record['employee_id']][record['date']].add(housing_id_out)
        
        # Process employee data
        all_employee_rows = []
        all_housing_used = set()
        
        for employee in employees:
            # Apply vacations and transfers
            attendance_by_date = defaultdict(dict)
            for day in dates:
                record = attendance_by_employee.get(employee.id, {}).get(day)
                if record:
                    attendance_by_date[day] = record
            
            # Apply vacations and transfers
            attendance_by_date = apply_vacations_and_transfers(
                employee.id, attendance_by_date, start_date, end_date
            )
            
            # Prepare attendance data for this employee
            attendance_data = []
            total_work_hours = 0
            total_overtime_hours = 0
            
            for day in dates:
                record = attendance_by_date.get(day)
                
                if record:
                    if isinstance(record, dict) and 'is_generated' in record:
                        # This is a generated record (vacation or transfer)
                        status = record['attendance_status']
                        record_dict = None
                    else:
                        # This is a real attendance record
                        status = record['attendance_status']
                        record_dict = record
                        
                        # Add work hours to totals
                        if record_dict:
                            total_work_hours += record_dict['work_hours']
                            total_overtime_hours += record_dict['overtime_hours']
                else:
                    # If no record, determine if it's a weekend or future date
                    if day.weekday() in weekend_days:
                        status = 'W'  # Weekend
                    elif day > date.today():
                        status = ''  # Future date
                    else:
                        status = 'A'  # Absent
                    record_dict = None
                
                # Add weekend information
                is_weekend = (day.weekday() in weekend_days)
                
                # Add to attendance data
                attendance_data.append({
                    'date': day,
                    'status': status,
                    'record': record_dict,
                    'is_weekend': is_weekend
                })
            
            # Get housing information
            housing_name = None
            if employee.housing_id:
                housing = Housing.query.get(employee.housing_id)
                if housing:
                    housing_name = housing.name
            
            # Create employee row
            employee_row = {
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'name_ar': employee.name_ar,
                'profession': employee.profession,
                'department_id': employee.department_id,
                'housing_id': employee.housing_id,
                'housing': housing_name,
                'attendance': attendance_data,
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'is_primary': True  # This is the primary record for this employee
            }
            
            all_employee_rows.append(employee_row)
        
        # Get department name if filter is applied
        department_name = None
        if department_id:
            department = Department.query.get(department_id)
            if department:
                department_name = department.name
        
        # Get housing name if filter is applied
        housing_name = None
        if housing_id:
            housing = Housing.query.get(housing_id)
            if housing:
                housing_name = housing.name
        
        # Sort employees by housing then by name
        all_employee_rows.sort(key=lambda x: (x.get('housing') or 'Unknown Housing', x.get('name') or ''))
        
        # Prepare final timesheet data
        timesheet_data = {
            'year': year,
            'month': month,
            'month_name': get_month_name(int(month)),
            'dates': dates,
            'employees': all_employee_rows,
            'total_employees': total_employees,
            'start_date': start_date,
            'end_date': end_date,
            'weekend_days': weekend_days,
            'department_name': department_name,
            'housing_name': housing_name,
            'working_days': month_period.days_in_month if month_period else None,
            'working_hours': month_period.hours_in_month if month_period else None
        }
        
        execution_time = time.time() - start_time
        logger.info(f"Generated timesheet data in {execution_time:.2f} seconds")
        
        return timesheet_data
        
    except Exception as e:
        logger.error(f"Error generating timesheet: {str(e)}")
        # Rollback any database changes if there was an error
        try:
            db.session.rollback()
        except:
            pass  # Ignore error if db is not initialized
        
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
