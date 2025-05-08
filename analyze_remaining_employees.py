"""
Script to analyze terminal usage for remaining employees without housing
"""
from app import app
from models import Employee, AttendanceRecord
from datetime import datetime, timedelta
from collections import defaultdict

with app.app_context():
    # Get all employees without housing
    employees_without_housing = Employee.query.filter(
        Employee.active == True,
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).all()
    
    # Analyze each employee's terminal usage
    print(f"Terminal Usage Analysis for {len(employees_without_housing)} Employees Without Housing\n")
    
    two_months_ago = datetime.now().date() - timedelta(days=60)
    
    # Count terminal usage across all employees
    all_terminal_usage = defaultdict(int)
    employees_per_terminal = defaultdict(list)
    
    for employee in employees_without_housing:
        # Get attendance records
        records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.date >= two_months_ago
        ).all()
        
        if not records:
            continue
        
        # Track terminal usage for this employee
        employee_terminals = set()
        
        # Count terminal usage
        for record in records:
            if record.terminal_alias_in:
                all_terminal_usage[record.terminal_alias_in] += 1
                employee_terminals.add(record.terminal_alias_in)
            if record.terminal_alias_out:
                all_terminal_usage[record.terminal_alias_out] += 1
                employee_terminals.add(record.terminal_alias_out)
        
        # Add employee to each terminal's list
        for terminal in employee_terminals:
            employees_per_terminal[terminal].append(employee.emp_code)
    
    # Display most common terminals
    print("Most commonly used terminals by employees without housing:")
    for terminal, count in sorted(all_terminal_usage.items(), key=lambda x: x[1], reverse=True)[:10]:
        emp_count = len(employees_per_terminal[terminal])
        emp_list = ", ".join(employees_per_terminal[terminal][:5])
        if len(employees_per_terminal[terminal]) > 5:
            emp_list += f" and {len(employees_per_terminal[terminal]) - 5} more"
        print(f"  - {terminal}: {count} uses by {emp_count} employees ({emp_list})")
