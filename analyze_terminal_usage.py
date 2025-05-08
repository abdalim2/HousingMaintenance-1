"""
Script to analyze terminal usage for employees without housing
"""
from app import app
from models import Employee, AttendanceRecord, BiometricTerminal, Housing
from datetime import datetime, timedelta
from collections import defaultdict

with app.app_context():
    # Get the 5 employees without housing
    employees_without_housing = Employee.query.filter(
        Employee.active == True,
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).limit(5).all()
    
    # Get mapping of terminals to housing
    terminal_to_housing = {}
    terminals = BiometricTerminal.query.all()
    for terminal in terminals:
        if terminal.housing_id:
            housing = Housing.query.get(terminal.housing_id)
            terminal_to_housing[terminal.terminal_alias] = housing.name if housing else "Unknown Housing"
    
    # Analyze each employee's terminal usage
    print("Analysis of Terminal Usage for Employees Without Housing\n")
    
    two_months_ago = datetime.now().date() - timedelta(days=60)
    
    for employee in employees_without_housing:
        print(f"Employee: {employee.emp_code} - {employee.name}")
        
        # Get attendance records
        records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.date >= two_months_ago
        ).all()
        
        if not records:
            print("  No attendance records found\n")
            continue
        
        # Count terminal usage
        terminal_usage = defaultdict(int)
        for record in records:
            if record.terminal_alias_in:
                terminal_usage[record.terminal_alias_in] += 1
            if record.terminal_alias_out and record.terminal_alias_out != record.terminal_alias_in:
                terminal_usage[record.terminal_alias_out] += 1
        
        # Display terminal usage with housing info
        print(f"  Total records: {len(records)}")
        print("  Terminal usage:")
        for terminal, count in sorted(terminal_usage.items(), key=lambda x: x[1], reverse=True):
            housing = terminal_to_housing.get(terminal, "Not associated with housing")
            print(f"    - {terminal}: {count} uses - Housing: {housing}")
        
        print("")
