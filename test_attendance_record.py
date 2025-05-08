from app import app
from models import db, AttendanceRecord
from datetime import datetime, date

with app.app_context():
    try:
        # Create a test AttendanceRecord entry
        test_record = AttendanceRecord(
            employee_id=1,
            date=date.today(),
            attendance_status="Present",
            weekday="Monday",
            clock_in="09:00",
            clock_out="17:00",
            terminal_alias_in="Terminal A",
            terminal_alias_out="Terminal A",
            work_hours=8.0,
            total_time="08:00",
            is_synced=True,
            sync_id=175  # Using the test sync log ID we just created
        )
        db.session.add(test_record)
        db.session.commit()
        print(f"Successfully created test AttendanceRecord with ID: {test_record.id}")
        
        # Verify by reading back
        record = AttendanceRecord.query.get(test_record.id)
        print(f"Retrieved: ID {record.id}, Employee: {record.employee_id}, Date: {record.date}, Is Synced: {record.is_synced}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
