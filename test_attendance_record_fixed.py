from app import app
from models import db, AttendanceRecord
from datetime import datetime, date, time

with app.app_context():
    try:
        # Create a test AttendanceRecord entry with proper datetime objects
        today = date.today()
        
        # Create time objects for clock_in and clock_out
        time_in = datetime.combine(today, time(9, 0))  # 9:00 AM
        time_out = datetime.combine(today, time(17, 0))  # 5:00 PM
        
        test_record = AttendanceRecord(
            employee_id=1,
            date=today,
            attendance_status="Present",
            weekday="Monday",
            clock_in=time_in,
            clock_out=time_out,
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
        record = AttendanceRecord.query.filter_by(id=test_record.id).first()
        print(f"Retrieved: ID {record.id}, Employee: {record.employee_id}, Date: {record.date}, Is Synced: {record.is_synced}")
        print(f"Clock in: {record.clock_in}, Clock out: {record.clock_out}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
