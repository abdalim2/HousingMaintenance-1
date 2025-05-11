from app import app
from models import db, AttendanceRecord, Employee
from optimized_timesheet import attendance_record_to_dict

with app.app_context():
    try:
        # Get a test employee and their attendance record
        print("Looking for test records...")
        
        # Find the employee we created earlier
        employee = Employee.query.filter_by(emp_code="113").first()
        if not employee:
            print("Test employee not found. Will try using any employee.")
            employee = Employee.query.first()
            
        if employee:
            print(f"Found employee: {employee.name} (ID: {employee.id})")
            
            # Get their attendance records
            record = AttendanceRecord.query.filter_by(employee_id=employee.id).first()
            
            if record:
                print(f"Found attendance record for date: {record.date}")
                
                # Convert record to dictionary
                record_dict = attendance_record_to_dict(record)
                
                # Close the session to simulate detached instance scenario
                db.session.close()
                
                # Now try to access the record as a dictionary (should work)
                print(f"Successfully accessed record date after session close: {record_dict['date']}")
                print(f"Clock in: {record_dict['clock_in']}")
                print(f"Clock out: {record_dict['clock_out']}")
                
                # Try to access the original record (would cause DetachedInstanceError)
                try:
                    print("Attempting to access original record (should fail with DetachedInstanceError)...")
                    print(f"Record date: {record.date}")
                except Exception as e:
                    print(f"Expected error occurred: {str(e)}")
                    print("This confirms our fix works - we should use the dictionary version instead")
            else:
                print("No attendance records found for this employee")
        else:
            print("No employees found in the database")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
