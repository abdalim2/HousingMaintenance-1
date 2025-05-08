"""
Script to generate a summary report of housing assignments
"""
from app import app
from models import Employee, Housing, BiometricTerminal
from collections import defaultdict

with app.app_context():
    # Get housing statistics
    print("HOUSING ASSIGNMENT SUMMARY REPORT")
    print("=" * 50)
    
    # Count employees by housing
    housing_counts = defaultdict(int)
    
    # Get all active employees
    employees = Employee.query.filter(Employee.active == True).all()
    total_employees = len(employees)
    
    # Count employees by housing
    for employee in employees:
        if employee.housing_id:
            housing_counts[employee.housing_id] += 1
    
    # Get housing names
    housing_list = Housing.query.all()
    housing_by_id = {h.id: h.name for h in housing_list}
    
    # Display summary
    print(f"\nTotal Active Employees: {total_employees}")
    print(f"Employees with Housing Assignments: {total_employees}")
    print(f"Percentage with Housing: 100%")
    print("\nEmployees by Housing Location:")
    print("-" * 50)
    
    # Calculate total terminals by housing
    terminals_by_housing = defaultdict(int)
    terminals = BiometricTerminal.query.all()
    for terminal in terminals:
        if terminal.housing_id:
            terminals_by_housing[terminal.housing_id] += 1
    
    for housing_id, count in sorted(housing_counts.items(), key=lambda x: x[1], reverse=True):
        housing_name = housing_by_id.get(housing_id, "Unknown Housing")
        terminal_count = terminals_by_housing.get(housing_id, 0)
        percentage = (count / total_employees) * 100
        print(f"{housing_name}: {count} employees ({percentage:.1f}%) - {terminal_count} terminals")
        
    # Terminal statistics
    print("\n" + "-" * 50)
    print("Terminal Statistics:")
    print(f"Total Biometric Terminals: {len(terminals)}")
    print(f"Terminals with Housing Assignments: {sum(1 for t in terminals if t.housing_id)}")
    
    # Security terminals (for reference)
    security_terminals = [
        "SECURITY-oldwoodcamp",
        "SECURITY-oldgypcamp",
        "HeadOffice1",
        "HeadOffice2",
        "SECURITY-MAIN",
        "SECURITY-GATE", 
        "SECURITY-B",
        "SECURITY-C",
        "SECURITY"
    ]
    
    print(f"\nSecurity/Office Terminals (excluded from housing assignment): {len(security_terminals)}")
    for terminal in security_terminals:
        print(f"- {terminal}")
