from app import app
from models import db, TempAttendance
from optimized_timesheet import temp_attendance_to_dict

with app.app_context():
    try:
        # Get a test TempAttendance record
        print("Looking for test TempAttendance records...")
        
        # Find a record
        temp_record = TempAttendance.query.filter_by(sync_id=175).first()
            
        if temp_record:
            print(f"Found TempAttendance record: {temp_record.first_name} {temp_record.last_name}, date: {temp_record.att_date}")
            
            # Convert to dictionary
            record_dict = temp_attendance_to_dict(temp_record)
            
            # Close the session to simulate detached instance scenario
            db.session.close()
            
            # Now try to access the dictionary (should work)
            print(f"Successfully accessed emp_code after session close: {record_dict['emp_code']}")
            print(f"First name: {record_dict['first_name']}")
            print(f"Last name: {record_dict['last_name']}")
            print(f"Att date: {record_dict['att_date']}")
            print(f"Punch time: {record_dict['punch_time']}")
            
            # Try to access the original record (would cause DetachedInstanceError)
            try:
                print("Attempting to access original record (should fail with DetachedInstanceError)...")
                print(f"Record date: {temp_record.att_date}")
            except Exception as e:
                print(f"Expected error occurred: {str(e)}")
                print("This confirms our fix works - we should use the dictionary version instead")
        else:
            print("No TempAttendance records found")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
