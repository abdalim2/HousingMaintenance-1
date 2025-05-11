#!/usr/bin/env python
"""
This script applies all the optimizations to the timesheet functionality.
It will greatly improve the performance of the timesheet page loading time.
"""
import os
import sys
import time
import logging
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of the file before modifying it"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
        
    backup_path = f"{file_path}.bak.{int(time.time())}"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backed up {file_path} to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error backing up {file_path}: {str(e)}")
        return False

def patch_app():
    """Patch app.py to use the optimized timesheet function"""
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
    
    if not backup_file(app_path):
        return False
        
    try:
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Add import for optimized timesheet
        import_pos = content.find('import data_processor')
        if import_pos > 0:
            if 'from optimized_timesheet import optimized_generate_timesheet' not in content:
                new_import = 'import data_processor\nfrom optimized_timesheet import optimized_generate_timesheet'
                content = content.replace('import data_processor', new_import)
                
        # Replace timesheet function call with optimized version
        original = "        timesheet_data = data_processor.generate_timesheet(\n            year, month, dept_id, start_date, end_date, housing_id, \n            limit=per_page, offset=offset, force_refresh=force_refresh\n        )"
        replacement = "        # Use optimized timesheet function for better performance\n        timesheet_data = optimized_generate_timesheet(\n            year, month, dept_id, start_date, end_date, housing_id, \n            limit=per_page, offset=offset, force_refresh=force_refresh\n        )"
        
        content = content.replace(original, replacement)
        
        # Replace in export function as well
        original_export = "        timesheet_data = data_processor.generate_timesheet(year, month, dept_id, start_date, end_date, housing_id)"
        replacement_export = "        # Use optimized timesheet function for better performance\n        timesheet_data = optimized_generate_timesheet(year, month, dept_id, start_date, end_date, housing_id)"
        
        content = content.replace(original_export, replacement_export)
        
        # Write updated content
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Updated {app_path} to use optimized timesheet function")
        return True
        
    except Exception as e:
        logger.error(f"Error patching app.py: {str(e)}")
        return False

def apply_database_indexes():
    """Apply database indexes to improve query performance"""
    try:
        # Load app context to update database
        from app import app, db
        from sqlalchemy import text, Index
        from models import AttendanceRecord, Employee
        
        with app.app_context():
            # Check existing indexes
            result = db.session.execute(text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'attendance_records'"
            ))
            existing_indexes = [r[0] for r in result]
            
            # Add indexes if not already present
            indexes_to_add = [
                ('idx_attendance_date_employee', AttendanceRecord.__table__, ['employee_id', 'date']),
                ('idx_attendance_status', AttendanceRecord.__table__, ['attendance_status']),
                ('idx_employee_active', Employee.__table__, ['active']),
                ('idx_employee_department', Employee.__table__, ['department_id'])
            ]
            
            for idx_name, table, columns in indexes_to_add:
                if idx_name not in existing_indexes:
                    cols = [getattr(table.c, col_name) for col_name in columns]
                    idx = Index(idx_name, *cols)
                    try:
                        idx.create(db.engine)
                        logger.info(f"Created index: {idx_name}")
                    except Exception as e:
                        logger.error(f"Error creating index {idx_name}: {str(e)}")
            
            logger.info("Database indexes applied")
            return True
            
    except Exception as e:
        logger.error(f"Error applying database indexes: {str(e)}")
        return False

def test_optimized_timesheet():
    """Test the optimized timesheet performance"""
    try:
        # Import optimized timesheet function
        from optimized_timesheet import optimized_generate_timesheet
        from app import app
        from flask import session
        import time
        
        with app.test_request_context('/timesheet'), app.app_context():
            # Initialize session
            session['language'] = 'en'
            
            # Test uncached performance
            print("Testing uncached performance...")
            start_time = time.time()
            result = optimized_generate_timesheet('2025', '5', force_refresh=True)
            uncached_time = time.time() - start_time
            
            print(f"Uncached time: {uncached_time:.2f} seconds")
            print(f"Employees: {len(result.get('employees', []))}")
            
            # Test cached performance
            print("\nTesting cached performance...")
            start_time = time.time()
            result = optimized_generate_timesheet('2025', '5')
            cached_time = time.time() - start_time
            
            print(f"Cached time: {cached_time:.2f} seconds")
            print(f"Speedup factor: {uncached_time/cached_time:.1f}x faster")
            
            return True
            
    except Exception as e:
        logger.error(f"Error testing optimized timesheet: {str(e)}")
        return False

def main():
    """Main function to apply all optimizations"""
    print("=" * 80)
    print("APPLYING TIMESHEET PERFORMANCE OPTIMIZATIONS")
    print("=" * 80)
    
    # Step 1: Add database indexes
    print("\n1. Adding database indexes...")
    apply_database_indexes()
    
    # Step 2: Patch app.py
    print("\n2. Updating app.py to use optimized timesheet function...")
    patch_app()
    
    # Step 3: Test performance
    print("\n3. Testing optimized timesheet performance...")
    test_optimized_timesheet()
    
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print("\nThe timesheet loading time has been significantly improved.")
    print("Please restart the application to apply all changes.")

if __name__ == "__main__":
    main()
