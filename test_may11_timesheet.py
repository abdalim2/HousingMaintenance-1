from flask import Flask, session, request
from database import db
from datetime import date
import json

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
app.secret_key = 'development-test-key'
db.init_app(app)

def test_timesheet_may11():
    """Test if the timesheet generation includes May 11, 2025 data"""
    from optimized_timesheet import optimized_generate_timesheet
    
    # Testing variables
    year = 2025
    month = 5
    
    # Create a request context - no need to use session for our test
    # We'll modify the optimized_timesheet.py to use a default weekend setting
    
    # First, call with force_refresh to ensure we get fresh data
    print("Generating fresh timesheet data...")
    timesheet_data = optimized_generate_timesheet(
        year, month, department_id=None, housing_id=None,
        force_refresh=True
    )
    
    # Number of employees
    print(f"Total employees in timesheet: {timesheet_data.get('total_employees', 0)}")
    print(f"Employees loaded in this batch: {timesheet_data.get('employees_loaded', 0)}")
    
    # Get all the dates in the timesheet
    dates = timesheet_data.get('dates', [])
    date_str_list = [d.strftime("%Y-%m-%d") for d in dates]
    print(f"Dates included in timesheet: {date_str_list}")
    
    # Check if May 11 is in the dates
    target_date = date(2025, 5, 11)
    if target_date in dates:
        print(f"May 11, 2025 IS included in the timesheet dates at index {dates.index(target_date)}")
    else:
        print("May 11, 2025 is NOT included in the timesheet dates!")
    
    # Check for employees with May 11 attendance
    employees = timesheet_data.get('employees', [])
    print(f"Number of employee records in timesheet: {len(employees)}")
    
    # Count employees with May 11 attendance
    employees_with_may11 = 0
    employees_with_may11_present = 0
    for employee in employees:
        attendance = employee.get('attendance', [])
        
        # Find May 11 attendance
        may11_attendance = None
        for att in attendance:
            if att['date'] == target_date:
                may11_attendance = att
                break
        
        if may11_attendance:
            employees_with_may11 += 1
            status = may11_attendance.get('status', 'Unknown')
            
            # If they have a 'P' status and an actual record, count as present
            if status == 'P' and may11_attendance.get('record') is not None:
                employees_with_may11_present += 1
    
    print(f"Employees with May 11 data: {employees_with_may11}")
    print(f"Employees marked PRESENT on May 11: {employees_with_may11_present}")
    
    # Print sample of employees with attendance on May 11
    print("\nSample employees with May 11 attendance:")
    count = 0
    for employee in employees:
        attendance = employee.get('attendance', [])
        may11_attendance = next((att for att in attendance if att['date'] == target_date), None)
        
        if may11_attendance and may11_attendance.get('status') == 'P' and may11_attendance.get('record') is not None:
            print(f"Employee: {employee.get('name')} (ID: {employee.get('id')})")
            print(f"  Status: {may11_attendance.get('status')}")
            
            # Print record details if it exists
            record = may11_attendance.get('record')
            if record:
                print(f"  Clock in: {record.get('clock_in')}")
                print(f"  Clock out: {record.get('clock_out')}")
                print(f"  Work hours: {record.get('work_hours')}")
                print(f"  Terminal in: {record.get('terminal_alias_in')}")
            
            count += 1
            if count >= 5:  # Print max 5 employees
                break

    return timesheet_data

with app.app_context():
    print("Starting timesheet test for May 11, 2025...")
    data = test_timesheet_may11()
    print("\nTest completed!")
