from flask import Flask
from database import db
from models import Department, Employee, AttendanceRecord, Housing, BiometricTerminal
import datetime
from datetime import date, timedelta
from collections import defaultdict

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
db.init_app(app)

def attendance_record_to_dict(record):
    """Convert an AttendanceRecord object to a dictionary."""
    if not record:
        return None
        
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
        'terminal_alias_out': record.terminal_alias_out
    }

def debug_timesheet_for_may11():
    """Debug the timesheet generation for May 11, 2025"""
    print("Debugging timesheet generation for May 11, 2025")
    
    # Set the year and month to May 2025
    year = 2025
    month = 5
    
    # Get May 2025 start and end dates
    start_date = date(year, month, 1)
    end_date = date(year, month, 31)
    
    print(f"Date range: {start_date} to {end_date}")
    
    # Get all dates in May 2025
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    print(f"Date list includes May 11? {date(2025, 5, 11) in dates}")
    
    # Get a few employees
    employees = Employee.query.filter(Employee.active == True).limit(10).all()
    print(f"Retrieved {len(employees)} employees")
    
    # Get employee IDs
    employee_ids = [e.id for e in employees]
    
    # Get attendance records for these employees in the date range
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id.in_(employee_ids),
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date
    ).all()
    
    print(f"Retrieved {len(attendance_records)} attendance records")
    
    # Check for May 11 records specifically
    may11_records = [r for r in attendance_records if r.date == date(2025, 5, 11)]
    print(f"Number of May 11 records found: {len(may11_records)}")
    
    # Convert to dictionaries (as the real function does)
    attendance_dict_records = [attendance_record_to_dict(record) for record in attendance_records]
    
    # Create attendance by employee data structure
    attendance_by_employee = defaultdict(dict)
    for idx, record in enumerate(attendance_records):
        record_dict = attendance_dict_records[idx]
        attendance_by_employee[record.employee_id][record.date] = record_dict
    
    # Create weekend days list (default to Fri/Sat)
    weekend_days = [4, 5]  # 4=Friday, 5=Saturday in Python's weekday system (0=Monday)
    
    # Check each employee
    for employee in employees:
        print(f"\nEmployee: {employee.name} (ID: {employee.id})")
        
        # Check if employee has May 11 attendance in the dictionary
        if date(2025, 5, 11) in attendance_by_employee.get(employee.id, {}):
            print(f"  HAS May 11 record in attendance_by_employee dictionary")
        else:
            print(f"  NO May 11 record in attendance_by_employee dictionary")
        
        # Process each date for this employee
        attendance_data = []
        for day in dates:
            record_dict = attendance_by_employee.get(employee.id, {}).get(day)
            
            if record_dict:
                status = record_dict['attendance_status']
                print(f"  {day}: Has record with status {status}")
            else:
                # Determine status for days without records
                if day.weekday() in weekend_days:
                    status = 'W'  # Weekend
                elif day > date.today():
                    status = ''  # Future date
                else:
                    status = 'A'  # Absent
                
                if day == date(2025, 5, 11):
                    print(f"  {day}: NO RECORD - assigned status '{status}'")
            
            # Add weekend information
            is_weekend = (day.weekday() in weekend_days)
            
            # Add to attendance data
            attendance_data.append({
                'date': day,
                'status': status,
                'record': record_dict,
                'is_weekend': is_weekend
            })
            
        # Check if May 11 is in the final attendance data
        may11_data = [d for d in attendance_data if d['date'] == date(2025, 5, 11)]
        if may11_data:
            print(f"  May 11 in final attendance data: Yes, status={may11_data[0]['status']}")
            print(f"  Record exists: {may11_data[0]['record'] is not None}")
        else:
            print(f"  May 11 in final attendance data: No")

with app.app_context():
    debug_timesheet_for_may11()
