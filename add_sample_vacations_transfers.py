"""
Script to add sample vacation and transfer records for testing
"""
from app import app
from models import db, Employee, EmployeeVacation, EmployeeTransfer, Department, Housing
from datetime import datetime, timedelta

def get_random_employees(count=3):
    """Get random active employees"""
    return Employee.query.filter_by(active=True).limit(count).all()

with app.app_context():
    # Get some employees
    employees = get_random_employees(5)
    
    if not employees:
        print("No active employees found.")
        exit()
    
    print(f"Adding sample data for {len(employees)} employees...")
    
    # Get current date
    today = datetime.now().date()
      # Get departments and housings for transfers
    departments = Department.query.all()
    housings = Housing.query.all()
    
    print(f"Found {len(departments)} departments and {len(housings)} housing locations.")
    
    # Continue even if we don't have enough departments/housings
    transfer_department = len(departments) >= 2
    transfer_housing = len(housings) >= 2
    
    # Create vacation records
    vacations_added = 0
    for i, employee in enumerate(employees):
        # Create a vacation for the current month
        vacation_start = today + timedelta(days=i*2)
        vacation_end = vacation_start + timedelta(days=7)  # 1 week vacation
        
        # Check if vacation already exists
        existing_vacation = EmployeeVacation.query.filter_by(
            employee_id=employee.id,
            start_date=vacation_start,
            end_date=vacation_end
        ).first()
        
        if not existing_vacation:
            vacation = EmployeeVacation(
                employee_id=employee.id,
                start_date=vacation_start,
                end_date=vacation_end,
                notes=f"Sample vacation for {employee.name}"
            )
            db.session.add(vacation)
            vacations_added += 1
      # Create transfer records
    transfers_added = 0
    for i, employee in enumerate(employees[:3]):  # Only use first 3 employees for transfers
        # Create a transfer for next month
        transfer_start = today + timedelta(days=15 + i*3)
        transfer_end = transfer_start + timedelta(days=14)  # 2 weeks transfer
        
        # Department transfer if we have enough departments
        if i == 0 and transfer_department:
            from_dept = departments[0]
            to_dept = departments[1]
            
            # Check if transfer already exists
            existing_transfer = EmployeeTransfer.query.filter_by(
                employee_id=employee.id,
                start_date=transfer_start,
                end_date=transfer_end,
                from_department_id=from_dept.id,
                to_department_id=to_dept.id
            ).first()
            
            if not existing_transfer:
                transfer = EmployeeTransfer(
                    employee_id=employee.id,
                    start_date=transfer_start,
                    end_date=transfer_end,
                    from_department_id=from_dept.id,
                    to_department_id=to_dept.id,
                    notes=f"Department transfer for {employee.name}"
                )
                db.session.add(transfer)
                transfers_added += 1
        
        # Housing transfer if we have enough housing locations
        elif i > 0 and transfer_housing:
            from_housing = housings[0]
            to_housing = housings[1]
            
            # Check if transfer already exists
            existing_transfer = EmployeeTransfer.query.filter_by(
                employee_id=employee.id,
                start_date=transfer_start,
                end_date=transfer_end,
                from_housing_id=from_housing.id,
                to_housing_id=to_housing.id
            ).first()
            
            if not existing_transfer:
                transfer = EmployeeTransfer(
                    employee_id=employee.id,
                    start_date=transfer_start,
                    end_date=transfer_end,
                    from_housing_id=from_housing.id,
                    to_housing_id=to_housing.id,
                    notes=f"Housing transfer for {employee.name}"
                )
                db.session.add(transfer)
                transfers_added += 1
    
    # Save changes
    db.session.commit()
    
    print(f"Added {vacations_added} vacation records and {transfers_added} transfer records.")
    
    # Show the records added
    print("\nVacations:")
    for vacation in EmployeeVacation.query.all():
        employee_name = vacation.employee.name if vacation.employee else "Unknown"
        print(f"- {employee_name}: {vacation.start_date} to {vacation.end_date}")
        
    print("\nTransfers:")
    for transfer in EmployeeTransfer.query.all():
        employee_name = transfer.employee.name if transfer.employee else "Unknown"
        if transfer.from_department_id and transfer.to_department_id:
            from_name = transfer.from_department.name if transfer.from_department else "Unknown"
            to_name = transfer.to_department.name if transfer.to_department else "Unknown"
            print(f"- {employee_name}: {transfer.start_date} to {transfer.end_date}, Dept: {from_name} → {to_name}")
        else:
            from_name = transfer.from_housing.name if transfer.from_housing else "Unknown"
            to_name = transfer.to_housing.name if transfer.to_housing else "Unknown"
            print(f"- {employee_name}: {transfer.start_date} to {transfer.end_date}, Housing: {from_name} → {to_name}")
