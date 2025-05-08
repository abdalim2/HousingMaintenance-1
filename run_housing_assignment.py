"""
Script to run the automatic housing assignment functionality
"""
from app import app, data_processor

with app.app_context():
    updated_count = data_processor.update_employee_housing_from_terminals()
    print(f"Updated housing for {updated_count} employees")
