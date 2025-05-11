from database import db
from flask import Flask
from models import AttendanceRecord, Employee
import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
db.init_app(app)

with app.app_context():
    # Check attendance records for May 11, 2025
    target_date = datetime.date(2025, 5, 11)
    
    # Query the database directly
    records = AttendanceRecord.query.filter_by(date=target_date).all()
    
    print(f"Found {len(records)} attendance records for {target_date}")
    
    # Get all employee ids with attendance on May 11
    employee_ids = [record.employee_id for record in records]
    print(f"Employees with attendance on May 11: {len(set(employee_ids))} unique employees")
    
    # Get the employee data for these ids
    employees = Employee.query.filter(Employee.id.in_(employee_ids)).all()
    print(f"Found {len(employees)} employee records")
    
    # Print the first few employees with their attendance
    for i, emp in enumerate(employees[:5]):
        print(f"\nEmployee {i+1}: {emp.name} (ID: {emp.id})")
        
        # Find this employee's attendance record for May 11
        record = next((r for r in records if r.employee_id == emp.id), None)
        if record:
            print(f"  Attendance status: {record.attendance_status}")
            print(f"  Clock in: {record.clock_in}")
            print(f"  Clock out: {record.clock_out}")
            print(f"  Work hours: {record.work_hours}")
            print(f"  Overtime hours: {record.overtime_hours}")
            print(f"  Terminal in: {record.terminal_alias_in}")
            print(f"  Terminal out: {record.terminal_alias_out}")
        else:
            print("  No attendance record found!")
