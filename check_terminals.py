"""
Script to check biometric terminals and their housing assignments
"""
from app import app
from models import BiometricTerminal, Housing

with app.app_context():
    # Get all terminals
    terminals = BiometricTerminal.query.all()
    
    print(f"Total terminals: {len(terminals)}")
    
    # Check terminals without housing
    unassigned = BiometricTerminal.query.filter(BiometricTerminal.housing_id.is_(None)).all()
    print(f"\nTerminals without housing assignment: {len(unassigned)}")
    for terminal in unassigned:
        print(f" - Terminal: {terminal.terminal_alias}, Device ID: {terminal.device_id}, Location: {terminal.location}")
    
    # Check terminals with housing
    assigned = BiometricTerminal.query.filter(BiometricTerminal.housing_id.isnot(None)).all()
    print(f"\nTerminals with housing assignment: {len(assigned)}")
    for terminal in assigned:
        housing = Housing.query.get(terminal.housing_id)
        housing_name = housing.name if housing else "Unknown Housing"
        print(f" - Terminal: {terminal.terminal_alias}, Housing: {housing_name}")
