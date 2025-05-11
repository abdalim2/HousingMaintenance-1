from app import app
from models import db, AttendanceRecord
from datetime import datetime, date

def attendance_record_to_dict(record):
    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "date": record.date,
        "attendance_status": record.attendance_status,
        "weekday": record.weekday,
        "clock_in": record.clock_in,
        "clock_out": record.clock_out,
        "terminal_alias_in": record.terminal_alias_in,
        "terminal_alias_out": record.terminal_alias_out,
        "work_hours": record.work_hours,
        "total_time": record.total_time,
        "is_synced": record.is_synced,
        "sync_id": record.sync_id
    }

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
        # Convert the retrieved AttendanceRecord to a dictionary
        record_dict = attendance_record_to_dict(record)
        print(f"Retrieved Record as Dict: {record_dict}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
