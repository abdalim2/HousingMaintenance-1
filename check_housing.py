
from database import db
from models import Housing, Employee, BiometricTerminal
from app import app

with app.app_context():
    print('=== Housing Records ===')
    housings = Housing.query.all()
    for housing in housings:
        print(f'ID: {housing.id}, Name: {housing.name}, Active: {housing.active}')
    
    print('\n=== Unknown Housing Employees ===')
    # Check employees with unknown housing
    unknown_employees_count = Employee.query.filter(
        (Employee.housing_id == None) | (Employee.housing_id == 0)
    ).count()
    print(f'Employees with NULL housing_id: {unknown_employees_count}')
    
    # Check terminals without housing
    print('\n=== Biometric Terminals Without Housing ===')
    terminals_without_housing = BiometricTerminal.query.filter(
        (BiometricTerminal.housing_id == None) | (BiometricTerminal.housing_id == 0)
    ).count()
    print(f'Terminals without housing_id: {terminals_without_housing}')
    
    # Print a few example terminals
    print('\n=== Sample Terminals ===')
    for terminal in BiometricTerminal.query.limit(5).all():
        housing_name = terminal.housing.name if terminal.housing else 'No Housing'
        print(f'Terminal: {terminal.terminal_alias}, Housing: {housing_name}, ID: {terminal.housing_id}')

