"""
Script to add missing terminals and associate them with housing
"""
from app import app
from models import BiometricTerminal, Housing
from database import db

# List of terminals to add with their housing assignments
# Format: (terminal_alias, device_id, location, housing_name)
terminals_to_add = [
    ("H-Umsalam-B2", "UMS-B2", "Um Salam Housing Block B2", "Bahra Housing Camp (King Abdul Aziz Hospital)"),
    ("SECURITY-oldwoodcamp", "SEC-OWC", "Security Checkpoint Old Wood Camp", "Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)"),
    ("ALAZIZIAH HOUSING", "AZH-01", "Al Aziziah Housing", "Makkah Housing Camp"),
    ("H-A.Khayatcamp-2", "KHC-02", "Al Khayat Camp Block 2", "Makkah Housing Camp (Zahir)"),
    ("ALTHOMAMA HOUSING CAMP", "THM-01", "Al Thomama Housing Camp", "Riyadh Remaal Housing Camp"),
    ("HKsauh-R1", "KSU-R1", "King Saud University Housing R1", "Riyadh King Saud University Housing Camp"),
    ("SHARMA-1", "SHR-01", "Sharma Housing Block 1", "Red Sea Housing Camp"),
    ("SHARMA", "SHR-00", "Sharma Housing Main", "Red Sea Housing Camp"),
    ("SHARMA-4", "SHR-04", "Sharma Housing Block 4", "Red Sea Housing Camp"),
    ("STEEL", "STL-01", "Steel Factory Housing", "Jeddah Housing Camp-Hamdaniah-(Old Gypsum Factory)"),
    ("SHARMA-2", "SHR-02", "Sharma Housing Block 2", "Red Sea Housing Camp")
]

with app.app_context():
    print("Adding missing terminals and associating them with housing...")
    
    # Get existing housings
    housings = {housing.name: housing.id for housing in Housing.query.all()}
    
    # Get existing terminals
    existing_terminals = {t.terminal_alias: t for t in BiometricTerminal.query.all()}
    
    added_count = 0
    updated_count = 0
    error_count = 0
    
    for terminal_alias, device_id, location, housing_name in terminals_to_add:
        try:
            # Skip if housing doesn't exist
            if housing_name not in housings:
                print(f"Error: Housing '{housing_name}' not found for terminal '{terminal_alias}'")
                error_count += 1
                continue
                
            housing_id = housings[housing_name]
            
            # Check if terminal already exists
            if terminal_alias in existing_terminals:
                # Update existing terminal
                terminal = existing_terminals[terminal_alias]
                terminal.device_id = device_id
                terminal.location = location
                terminal.housing_id = housing_id
                updated_count += 1
                print(f"Updated terminal: {terminal_alias} -> {housing_name}")
            else:
                # Create new terminal
                terminal = BiometricTerminal(
                    terminal_alias=terminal_alias,
                    device_id=device_id,
                    location=location,
                    housing_id=housing_id
                )
                db.session.add(terminal)
                added_count += 1
                print(f"Added new terminal: {terminal_alias} -> {housing_name}")
        
        except Exception as e:
            print(f"Error processing terminal '{terminal_alias}': {str(e)}")
            error_count += 1
    
    # Commit changes
    if added_count > 0 or updated_count > 0:
        try:
            db.session.commit()
            print(f"\nSummary:\n- Added: {added_count} terminals\n- Updated: {updated_count} terminals\n- Errors: {error_count}")
            print("Changes committed successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {str(e)}")
    else:
        print("No changes were made.")
