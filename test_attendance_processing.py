from app import app
from models import db, TempAttendance, AttendanceRecord
from sync_service import process_attendance_data
from datetime import datetime, date

with app.app_context():
    try:
        # Get the latest TempAttendance records (up to 10 for testing)
        temp_records = TempAttendance.query.limit(10).all()
        print(f"Found {len(temp_records)} temporary attendance records")
        
        if temp_records:
            # Process the temporary records manually
            print("Processing temporary records...")
            
            # Create fake sync log ID for testing
            test_sync_id = 175
            
            # Call the processing function with the existing temp records
            process_attendance_data(db, test_sync_id)
            
            # Check if new AttendanceRecord entries were created
            new_attendance_records = AttendanceRecord.query.filter_by(sync_id=test_sync_id).all()
            print(f"Created {len(new_attendance_records)} new attendance records")
            
            for record in new_attendance_records[:5]:  # Show first 5 records
                print(f"- Employee ID: {record.employee_id}, Date: {record.date}, Clock in: {record.clock_in}, Clock out: {record.clock_out}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
