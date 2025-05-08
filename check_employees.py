from app import app
from models import db, Employee, Department

with app.app_context():
    employees = Employee.query.all()
    print(f"Found {len(employees)} employees:")
    
    for employee in employees:
        print(f"- ID: {employee.id}, Code: {employee.emp_code}, Name: {employee.name}")
    
    if not employees:
        # Create a test department if none exists
        department = Department.query.first()
        if not department:
            department = Department(dept_id="TEST01", name="Test Department")
            db.session.add(department)
            db.session.commit()
            print(f"Created test department with ID: {department.id}")
        else:
            print(f"Using existing department with ID: {department.id}")
        
        # Create a test employee
        try:
            test_employee = Employee(
                emp_code="EMP001",
                name="Test Employee",
                department_id=department.id,
                active=True
            )
            db.session.add(test_employee)
            db.session.commit()
            print(f"Created test employee with ID: {test_employee.id}")
        except Exception as e:
            print(f"Error creating test employee: {str(e)}")
            db.session.rollback()
