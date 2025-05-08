"""
Script to add vacation and transfer tables to the database
"""
from app import app
from models import db, EmployeeVacation, EmployeeTransfer

print("Adding vacation and transfer tables to database...")

with app.app_context():
    # Create the new tables
    db.create_all()
    
    print("Tables created successfully")
    print("- employee_vacations: to track employee vacation periods")
    print("- employee_transfers: to track employee transfers between departments/housings")
    print("Done!")
