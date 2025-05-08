from app import app
from models import db, AttendanceRecord, Employee
from datetime import datetime, date, time

with app.app_context():
    try:
        # Get an existing employee
        employee = Employee.query.filter_by(id=113).first()  # Using employee ID 113 (Bilal Kazi)
        
        if employee:
            print(f"Using employee: {employee.name} (ID: {employee.id})")
            
            # Create a test AttendanceRecord entry with proper datetime objects
            today = date.today()
            
            # Create time objects for clock_in and clock_out
            time_in = datetime.combine(today, time(9, 0))  # 9:00 AM
            time_out = datetime.combine(today, time(17, 0))  # 5:00 PM
            
            test_record = AttendanceRecord(
                employee_id=employee.id,
                date=today,
                attendance_status="Present",
                weekday="Thursday",  # May 8, 2025 is a Thursday
                clock_in=time_in,
                clock_out=time_out,
                terminal_alias_in="Terminal A",
                terminal_alias_out="Terminal A",
                work_hours=8.0,
                total_time="08:00",
                is_synced=True,
                sync_id=175  # Using the test sync log ID we created earlier
            )
            db.session.add(test_record)
            db.session.commit()
            print(f"Successfully created test AttendanceRecord with ID: {test_record.id}")
            
            # Verify by reading back
            record = AttendanceRecord.query.filter_by(id=test_record.id).first()
            print(f"Retrieved: ID {record.id}, Employee: {record.employee.name}, Date: {record.date}")
            print(f"Clock in: {record.clock_in}, Clock out: {record.clock_out}, Is Synced: {record.is_synced}")
        else:
            print("Could not find employee with ID 113")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
