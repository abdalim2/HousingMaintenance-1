"""
Script to manually assign housing for remaining employees without housing assignments
"""
from app import app
from models import Employee, BiometricTerminal, Housing
from database import db

with app.app_context():
    # Get all employees without housing
    employees_without_housing = Employee.query.filter(
        Employee.active == True,
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).all()
    
    print(f"Found {len(employees_without_housing)} employees without housing assignments")
    
    # Get all housing locations
    housings = Housing.query.all()
    housing_by_id = {h.id: h for h in housings}
    
    # Define manual housing assignments based on terminal usage patterns
    # Maps employee codes to housing IDs
    manual_assignments = {
        # SECURITY-oldwoodcamp users primarily work at the Jeddah Housing Camp-Hamdaniah
        # These are the employees who frequently use the SECURITY-oldwoodcamp terminal
        "34187": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49237": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "28590": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49491": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49498": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49902": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "45768": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49112": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "49545": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "28824": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "29820": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        
        # HeadOffice1 users likely work at Jeddah Head Office
        "40097": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        
        # Remaining employees can be assigned to Jeddah Housing Camp as default
        "50541": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "41852": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "40666": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "37475": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "48877": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "31435": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "44773": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "50674": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "50675": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
        "50577": 4,  # Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)
    }
    
    # Apply manual assignments
    updated_count = 0
    for employee in employees_without_housing:
        if employee.emp_code in manual_assignments:
            housing_id = manual_assignments[employee.emp_code]
            housing_name = housing_by_id[housing_id].name if housing_id in housing_by_id else "Unknown"
            
            employee.housing_id = housing_id
            updated_count += 1
            print(f"Assigned employee {employee.emp_code} ({employee.name}) to {housing_name}")
    
    # Save changes
    if updated_count > 0:
        db.session.commit()
        print(f"\nSuccessfully assigned housing for {updated_count} employees")
    else:
        print("No housing assignments were made")
