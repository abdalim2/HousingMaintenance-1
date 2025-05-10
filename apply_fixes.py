#!/usr/bin/env python
"""
Fix script for HousingMaintenance-4 system

This script:
1. Adds the missing 'notes' column to AttendanceRecord model
2. Updates the environment variable name for departments in the settings
"""
import os
import sys
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_missing_notes_column():
    """Add missing notes column to AttendanceRecord table"""
    try:
        from app import app, db
        from models import AttendanceRecord
        
        with app.app_context():
            # Check if column already exists
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name = 'attendance_records' AND column_name = 'notes';")
            result = db.session.execute(check_sql).fetchone()
            
            if result:
                logger.info("'notes' column already exists in attendance_records table. No changes needed.")
                return
                
            # Add the notes column
            alter_sql = text("ALTER TABLE attendance_records ADD COLUMN notes TEXT;")
            db.session.execute(alter_sql)
            db.session.commit()
            
            logger.info("Successfully added 'notes' column to attendance_records table.")
    except Exception as e:
        logger.error(f"Error adding 'notes' column: {str(e)}")
        raise

def fix_department_settings():
    """Fix the departments variable name in app.py & sync_service.py"""
    try:
        from app import app, sync_service
        
        # First, check if there are existing department settings
        current_departments = []
        
        # Get current departments from environment or sync_service
        if hasattr(sync_service, 'DEPARTMENTS'):
            current_departments = sync_service.DEPARTMENTS
            logger.info(f"Found current departments in sync_service: {current_departments}")
            
            # Update environment variable with correct name
            departments_str = ','.join(map(str, current_departments))
            os.environ['DEPARTMENTS'] = departments_str
            logger.info(f"Updated DEPARTMENTS environment variable to: {departments_str}")
        
        logger.info("Department settings fix applied successfully.")
    except Exception as e:
        logger.error(f"Error fixing department settings: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Fix 1: Add missing notes column
        logger.info("Applying fix for missing 'notes' column...")
        fix_missing_notes_column()
        
        # Fix 2: Department settings variable
        logger.info("Applying fix for department settings...")
        fix_department_settings()
        
        logger.info("All fixes applied successfully!")
    except Exception as e:
        logger.error(f"Error applying fixes: {str(e)}")
        sys.exit(1)
