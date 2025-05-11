from app import app
from models import db, Employee
from optimized_timesheet import optimized_generate_timesheet

with app.app_context():
    try:
        # Get a test employee
        employee = Employee.query.filter_by(emp_code="113").first()
        if not employee:
            print("Test employee not found. Will try using any employee.")
            employee = Employee.query.first()
            
        if employee:
            print(f"Testing timesheet for employee: {employee.name} (ID: {employee.id})")
              # Generate timesheet using the fixed code
            result = optimized_generate_timesheet(2025, 5, limit=10)
            print(f"Successfully generated timesheet with {len(result['employees'])} employee records")
            
            # Check if we have any employees in the result
            if result['employees']:
                print(f"Employee in result: {result['employees'][0]['name']}")
                
                # Check for any attendance records
                if result['employees'][0]['attendance_data']:
                    print(f"First attendance record date: {result['employees'][0]['attendance_data'][0]['date']}")
                    print(f"Status: {result['employees'][0]['attendance_data'][0]['status']}")
                    if 'record' in result['employees'][0]['attendance_data'][0] and result['employees'][0]['attendance_data'][0]['record']:
                        print("Record exists and is properly converted to dictionary")
                        record = result['employees'][0]['attendance_data'][0]['record']
                        print(f"Record type: {type(record)}")
                        print(f"Record contents: {record}")
                    else:
                        print("Record is None or not properly converted to dictionary")
                else:
                    print("No attendance records found for this employee")
            else:
                print("No employees found in the timesheet result")
            
        else:
            print("No employees found in the database")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
