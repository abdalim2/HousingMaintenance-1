from app import app
from models import db, TempAttendance
from datetime import datetime, date

with app.app_context():
    try:
        # Create a test TempAttendance entry
        test_record = TempAttendance(
            emp_code="113",
            first_name="Test",
            last_name="User",
            dept_name="HOUSING",
            att_date=date.today(),
            punch_time="09:00",
            punch_state="Check-in",
            terminal_alias="Terminal A",
            sync_id=175  # Using the test sync log ID
        )
        db.session.add(test_record)
        db.session.commit()
        print(f"Successfully created test TempAttendance with ID: {test_record.id}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
