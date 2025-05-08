"""
Script to identify terminals that need to be associated with housing
"""
from app import app
from models import BiometricTerminal, AttendanceRecord
from collections import defaultdict
from sqlalchemy import func

with app.app_context():
    # Find terminals referenced in attendance records that don't exist in the terminals table
    print("Terminals referenced in attendance records but not in terminals database:")
    
    # Get all unique terminal_alias_in values from attendance records
    terminal_aliases_in = AttendanceRecord.query.with_entities(
        AttendanceRecord.terminal_alias_in, 
        func.count(AttendanceRecord.id).label('count')
    ).filter(AttendanceRecord.terminal_alias_in != None).group_by(
        AttendanceRecord.terminal_alias_in
    ).all()
    
    # Get all unique terminal_alias_out values from attendance records
    terminal_aliases_out = AttendanceRecord.query.with_entities(
        AttendanceRecord.terminal_alias_out, 
        func.count(AttendanceRecord.id).label('count')
    ).filter(AttendanceRecord.terminal_alias_out != None).group_by(
        AttendanceRecord.terminal_alias_out
    ).all()
    
    # Combine the terminal aliases from both in and out
    all_terminal_aliases = defaultdict(int)
    for alias, count in terminal_aliases_in:
        all_terminal_aliases[alias] += count
    
    for alias, count in terminal_aliases_out:
        all_terminal_aliases[alias] += count
    
    # Get all terminals in the database
    existing_terminals = {t.terminal_alias: t for t in BiometricTerminal.query.all()}
    
    # Find terminals that are not in the database
    missing_terminals = []
    for alias, count in all_terminal_aliases.items():
        if alias not in existing_terminals:
            missing_terminals.append((alias, count))
    
    # Sort by frequency of use
    missing_terminals.sort(key=lambda x: x[1], reverse=True)
    
    if missing_terminals:
        for alias, count in missing_terminals:
            print(f"  - {alias}: used {count} times")
    else:
        print("  No missing terminals found.")

    # Find terminals without housing assignments
    print("\nExisting terminals without housing assignments:")
    unassigned_terminals = BiometricTerminal.query.filter(BiometricTerminal.housing_id.is_(None)).all()
    
    if unassigned_terminals:
        for terminal in unassigned_terminals:
            print(f"  - {terminal.terminal_alias}")
    else:
        print("  No unassigned terminals found.")
        
    # Check common terminals that might need housing assignment
    print("\nMost common terminal aliases in attendance records:")
    for alias, count in sorted(all_terminal_aliases.items(), key=lambda x: x[1], reverse=True)[:10]:
        terminal = existing_terminals.get(alias)
        housing_info = f"Housing ID: {terminal.housing_id}" if terminal and terminal.housing_id else "No housing assigned"
        print(f"  - {alias}: used {count} times - {housing_info}")
