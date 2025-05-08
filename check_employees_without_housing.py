"""
Script to check employees without housing assignments
"""
from app import app
from models import Employee

with app.app_context():
    # Get employees without housing
    employees_without_housing = Employee.query.filter(
        Employee.active == True,
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).all()
    
    print(f"Total employees without housing: {len(employees_without_housing)}")
    
    # List the first 20 employees without housing
    print("\nFirst 20 employees without housing:")
    for i, emp in enumerate(employees_without_housing[:20]):
        print(f"{i+1}. {emp.emp_code}: {emp.name}")
    
    # Group by department
    dept_count = {}
    for emp in employees_without_housing:
        dept_name = emp.department.name if emp.department else "No Department"
        dept_count[dept_name] = dept_count.get(dept_name, 0) + 1
    
    print("\nEmployees without housing by department:")
    for dept, count in dept_count.items():
        print(f"{dept}: {count} employees")
