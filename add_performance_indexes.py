#!/usr/bin/env python
"""
This script adds performance-related indexes to the database to improve query speed
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set correct path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app and db
from app import app
from database import db

def add_performance_indexes():
    """
    Add performance indexes to critical tables
    """
    try:
        with app.app_context():
            # Add indexes to attendance_records table
            logger.info("Adding indexes to attendance_records table...")
            
            # Index on employee_id and date (most frequent query filter)
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance_records (employee_id, date)')
            
            # Index on date alone for date range queries
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_records (date)')
            
            # Index on terminal IDs for terminal-based queries
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_attendance_terminal_in ON attendance_records (terminal_id_in)')
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_attendance_terminal_out ON attendance_records (terminal_id_out)')
            
            # Add indexes to employees table
            logger.info("Adding indexes to employees table...")
            
            # Index on active status - we usually only query active employees
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_active ON employees (active)')
            
            # Index on department_id and housing_id for filtering
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_department ON employees (department_id)')
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_housing ON employees (housing_id)')
            
            # Add compound index for department + active
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_dept_active ON employees (department_id, active)')
            
            # Add compound index for housing + active
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_housing_active ON employees (housing_id, active)')
            
            # Adding additional index for employee name search
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_employee_name ON employees (name)')
            
            # Add indexes to biometric_terminals table
            logger.info("Adding indexes to biometric_terminals table...")
            db.session.execute('CREATE INDEX IF NOT EXISTS idx_terminal_housing ON biometric_terminals (housing_id)')
            
            db.session.commit()
            logger.info("Successfully added all performance indexes")
            return True
    except Exception as e:
        logger.error(f"Error adding indexes: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    success = add_performance_indexes()
    if success:
        print("✅ Successfully added performance indexes to database")
    else:
        print("❌ Failed to add performance indexes to database")
