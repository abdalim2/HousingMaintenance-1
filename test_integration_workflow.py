"""
Integration test for the full workflow from temporary attendance creation
to timesheet generation, making sure both fixes are working correctly:
1. TempAttendance employee_id attribute fix
2. DetachedInstanceError prevention using dictionaries
"""

import os
import sys
from datetime import datetime, date, timedelta
from app import app, db
from models import Employee, TempAttendance, AttendanceRecord, Department
from sync_service import process_attendance_data
from optimized_timesheet import optimized_generate_timesheet, temp_attendance_to_dict
from db_utils import convert_db_results, safe_db_operation

# Set up testing environment
TEST_EMP_CODE = "113"  # Use an existing employee code or create a test one

def create_test_temp_record(db_session, emp_code):
    """Create a test temporary attendance record"""
    today = date.today()
    
    # Morning check-in
    morning_record = TempAttendance(
        emp_code=emp_code,
        first_name="Test",
        last_name="Employee",
        dept_name="IT",
        att_date=today,
        punch_time="08:00",  # Format expected by process_attendance_data
        punch_state="Check In",
        terminal_alias="Main Entrance",
        sync_id=999,  # Test sync ID
        created_at=datetime.now()
    )
    
    # Evening check-out
    evening_record = TempAttendance(
        emp_code=emp_code,
        first_name="Test",
        last_name="Employee",
        dept_name="IT",
        att_date=today,
        punch_time="17:00",  # Format expected by process_attendance_data
        punch_state="Check Out",
        terminal_alias="Main Entrance",
        sync_id=999,  # Test sync ID
        created_at=datetime.now()
    )
    
    db_session.add(morning_record)
    db_session.add(evening_record)
    db_session.commit()
    
    return [morning_record, evening_record]

def verify_temp_attendance_conversion(temp_records):
    """Test the conversion of TempAttendance objects to dictionaries"""
    print("\n[TEST 1] Testing TempAttendance conversion to dictionaries...")
    
    # Convert records to dictionaries
    temp_record_dicts = [temp_attendance_to_dict(record) for record in temp_records]
    
    # Close the session to simulate detached instance scenario
    db.session.close()
    
    # Try to access dictionary values (should work)
    try:
        for i, record_dict in enumerate(temp_record_dicts):
            print(f"Record {i+1}:")
            print(f"  Emp code: {record_dict['emp_code']}")
            print(f"  Name: {record_dict['first_name']} {record_dict['last_name']}")
            print(f"  Date: {record_dict['att_date']}")
            print(f"  Punch time: {record_dict['punch_time']}")
            print(f"  Punch state: {record_dict['punch_state']}")
        print("✅ SUCCESS: Successfully accessed dictionary values after session closure")
        return True
    except Exception as e:
        print(f"❌ FAILED: Error accessing dictionary values: {str(e)}")
        return False

def verify_attendance_processing(sync_id=999):
    """Test the attendance processing from TempAttendance to AttendanceRecord"""
    print("\n[TEST 2] Testing attendance processing...")
    
    try:
        # Process the temporary records
        process_attendance_data(db, sync_id)
        
        # Check if AttendanceRecord entries were created
        new_records = AttendanceRecord.query.filter_by(sync_id=sync_id).all()
        if not new_records:
            print("❌ FAILED: No attendance records created")
            return False
            
        print(f"✅ SUCCESS: Created {len(new_records)} attendance records")
        
        # Verify record details
        record = new_records[0]
        print(f"  Employee ID: {record.employee_id}")
        print(f"  Date: {record.date}")
        print(f"  Clock in: {record.clock_in}")
        print(f"  Clock out: {record.clock_out}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: Error during attendance processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_timesheet_generation():
    """Test timesheet generation with the fixed code"""
    print("\n[TEST 3] Testing timesheet generation...")
    
    try:
        # Get current month and year
        today = date.today()
        month = today.month
        year = today.year
        
        # Generate timesheet
        result = optimized_generate_timesheet(year, month, limit=10)
        
        if not result or 'employees' not in result:
            print("❌ FAILED: No timesheet result returned")
            return False
            
        print(f"✅ SUCCESS: Generated timesheet with {len(result['employees'])} employee records")
        
        # Check if we have any employees in the result
        if result['employees']:
            employee = result['employees'][0]
            print(f"  Employee: {employee['name']}")
            
            # Check attendance data
            if 'attendance_data' in employee and employee['attendance_data']:
                attendance = employee['attendance_data'][0]
                print(f"  First attendance date: {attendance['date']}")
                print(f"  Status: {attendance['status']}")
                
                # Check for any record dictionaries (converted from AttendanceRecord)
                if 'record' in attendance and attendance['record']:
                    print("  Record exists and is properly converted to dictionary")
                    print(f"  Record type: {type(attendance['record'])}")
                    return True
            else:
                print("  No attendance data found")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: Error during timesheet generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_integration_test():
    """Run the full integration test"""
    with app.app_context():
        try:
            print("\n===== INTEGRATION TEST STARTED =====\n")
            
            # Step 1: Find or create test department
            department = Department.query.filter_by(name="IT").first()
            if not department:
                print("Creating test department...")
                department = Department(
                    dept_id="IT001",  # Providing the required dept_id field
                    name="IT",
                    active=True
                )
                db.session.add(department)
                db.session.commit()
                print(f"Created test department: {department.name}, ID: {department.id}")
            else:
                print(f"Using existing department: {department.name}, ID: {department.id}")
              # Step 2: Find or create test employee
            employee = Employee.query.filter_by(emp_code=TEST_EMP_CODE).first()
            if not employee:
                print(f"Test employee with emp_code {TEST_EMP_CODE} not found. Creating one...")
                employee = Employee(
                    emp_code=TEST_EMP_CODE,
                    name="Test Employee",
                    department_id=department.id,  # Link to the department
                    profession="Developer",
                    active=True
                )
                db.session.add(employee)
                db.session.commit()
                print(f"Created test employee: {employee.name}, ID: {employee.id}")
            else:
                print(f"Using existing employee: {employee.name}, ID: {employee.id}")
            
            # Step 3: Create test temp attendance records
            print("\nCreating test temporary attendance records...")
            temp_records = create_test_temp_record(db.session, TEST_EMP_CODE)
            print(f"Created {len(temp_records)} temporary attendance records")
            
            # Step 3: Test TempAttendance conversion
            temp_conversion_success = verify_temp_attendance_conversion(temp_records)
            
            # Step 4: Test attendance processing
            attendance_success = verify_attendance_processing(sync_id=999)
            
            # Step 5: Test timesheet generation
            timesheet_success = verify_timesheet_generation()
            
            # Summary
            print("\n===== INTEGRATION TEST RESULTS =====")
            print(f"TempAttendance Conversion: {'✅ PASS' if temp_conversion_success else '❌ FAIL'}")
            print(f"Attendance Processing: {'✅ PASS' if attendance_success else '❌ FAIL'}")
            print(f"Timesheet Generation: {'✅ PASS' if timesheet_success else '❌ FAIL'}")
            
            overall = temp_conversion_success and attendance_success and timesheet_success
            print(f"\nOVERALL RESULT: {'✅ PASS' if overall else '❌ FAIL'}")
            
        except Exception as e:
            print(f"\n❌ INTEGRATION TEST FAILED with error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_integration_test()
