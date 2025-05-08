"""
Script to assign housing for the final remaining employees without housing
"""
from app import app
from models import Employee, Housing
from database import db

with app.app_context():
    # Get the final employees without housing
    final_employees = Employee.query.filter(
        Employee.active == True,
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).all()
    
    print(f"Found {len(final_employees)} remaining employees without housing")
    
    # Define final manual assignments
    # These employees likely have similar names to others who already have housing assignments
    manual_assignments = {
        "44803": 2,  # Makkah Housing Camp (for Usama Jamil Muhammad Ja)
        "44775": 9,  # Riyadh Remaal Housing Camp (for Mohammad Shahnawaz Mohammad Maksud Alam)
        "44817": 8,  # Riyadh King Saud University Housing Camp (for Khurshed Alam Makbul Alam)
    }
    
    # Apply the final assignments
    updated_count = 0
    for employee in final_employees:
        if employee.emp_code in manual_assignments:
            housing_id = manual_assignments[employee.emp_code]
            
            # Get housing name for logging
            housing = Housing.query.get(housing_id)
            housing_name = housing.name if housing else "Unknown Housing"
            
            # Assign housing
            employee.housing_id = housing_id
            updated_count += 1
            print(f"Assigned employee {employee.emp_code} ({employee.name}) to {housing_name}")
    
    # Save changes
    if updated_count > 0:
        db.session.commit()
        print(f"\nSuccessfully assigned housing for final {updated_count} employees")
    else:
        print("No additional housing assignments were made")
