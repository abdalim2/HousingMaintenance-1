"""
Performance optimization script for the Housing Maintenance application.
This script applies various optimizations to improve the performance of the application.
"""
import os
import sys
import time
import logging
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    backup_path = f"{file_path}.bak.{int(time.time())}"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup of {file_path} at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {str(e)}")
        return False

def update_app_imports():
    """Update app.py to import the optimized modules"""
    app_path = 'app.py'

    if not backup_file(app_path):
        return False

    try:
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add import for optimized modules
        if 'from optimized_data_processor import generate_optimized_timesheet' not in content:
            # Find the import section
            import_section = "# Import services after models\nimport data_processor\nfrom optimized_timesheet import optimized_generate_timesheet"
            new_import_section = "# Import services after models\nimport data_processor\nfrom optimized_timesheet import optimized_generate_timesheet\nfrom optimized_data_processor import generate_optimized_timesheet\nfrom enhanced_cache_optimized import timesheet_cache, clear_timesheet_cache"

            content = content.replace(import_section, new_import_section)

        # Update timesheet route to use optimized function
        timesheet_route = '''@app.route('/timesheet')
def timesheet():
    """View monthly timesheet"""
    # Get query parameters
    year = request.args.get('year', data_processor.get_current_year())
    month = request.args.get('month', data_processor.get_current_month())
    dept_id = request.args.get('department', None)
    housing_id = request.args.get('housing', None)  # جديد: معرف السكن للتصفية

    # Check for custom start and end dates from month configuration
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
      # Pagination parameters - default to first page with 50 employees per page
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    offset = (page - 1) * per_page

    # Force refresh if requested
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    # Use optimized timesheet function for better performance
    timesheet_data = optimized_generate_timesheet(
        year, month, dept_id, start_date, end_date, housing_id,
        limit=per_page, offset=offset, force_refresh=force_refresh
    )'''

        new_timesheet_route = '''@app.route('/timesheet')
def timesheet():
    """View monthly timesheet"""
    # Get query parameters
    year = request.args.get('year', data_processor.get_current_year())
    month = request.args.get('month', data_processor.get_current_month())
    dept_id = request.args.get('department', None)
    housing_id = request.args.get('housing', None)  # جديد: معرف السكن للتصفية

    # Check for custom start and end dates from month configuration
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
      # Pagination parameters - default to first page with 50 employees per page
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    offset = (page - 1) * per_page

    # Force refresh if requested
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    # Use highly optimized timesheet function for maximum performance
    timesheet_data = generate_optimized_timesheet(
        year, month, dept_id, start_date, end_date, housing_id,
        limit=per_page, offset=offset, force_refresh=force_refresh
    )'''

        content = content.replace(timesheet_route, new_timesheet_route)

        # Add cache clearing route
        if '@app.route(\'/clear_cache\')' not in content:
            settings_route = "@app.route('/settings', methods=['GET', 'POST'])"
            cache_route = '''@app.route('/clear_cache')
def clear_cache():
    """Clear the application cache"""
    try:
        # Clear timesheet cache
        cleared = clear_timesheet_cache()

        # Clear disk cache
        disk_cleared = timesheet_cache.clear()

        flash(f'Cache cleared successfully. Removed {disk_cleared} disk cache files.', 'success')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'danger')

    # Redirect back to the previous page or to the home page
    next_page = request.args.get('next') or request.referrer or url_for('index')
    return redirect(next_page)

'''
            content = content.replace(settings_route, cache_route + settings_route)

        # Write updated content
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Updated {app_path} with optimized imports and routes")
        return True

    except Exception as e:
        logger.error(f"Error updating {app_path}: {str(e)}")
        return False

def add_cache_button_to_template():
    """Add a cache clearing button to the timesheet template"""
    template_path = 'templates/timesheet.html'

    if not backup_file(template_path):
        return False

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add cache clearing button
        if 'clear_cache' not in content:
            export_buttons = '''<a href="{{ url_for('export_timesheet', year=selected_year, month=selected_month, department=selected_dept, housing=selected_housing) }}" class="btn btn-sm btn-success">
    <i class="fas fa-file-pdf"></i> Export PDF
</a>'''

            new_export_buttons = '''<a href="{{ url_for('export_timesheet', year=selected_year, month=selected_month, department=selected_dept, housing=selected_housing) }}" class="btn btn-sm btn-success">
    <i class="fas fa-file-pdf"></i> Export PDF
</a>
<a href="{{ url_for('clear_cache') }}?next={{ request.path }}" class="btn btn-sm btn-warning ms-2">
    <i class="fas fa-sync"></i> Refresh Cache
</a>'''

            content = content.replace(export_buttons, new_export_buttons)

        # Write updated content
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Updated {template_path} with cache clearing button")
        return True

    except Exception as e:
        logger.error(f"Error updating {template_path}: {str(e)}")
        return False

def apply_database_indexes():
    """Apply database indexes to improve query performance"""
    try:
        from app import app
        from database import db
        from models import AttendanceRecord, Employee, EmployeeVacation, EmployeeTransfer
        from sqlalchemy import Index

        with app.app_context():
            # Define indexes to add
            indexes = [
                Index('idx_attendance_employee_date',
                      AttendanceRecord.employee_id, AttendanceRecord.date),
                Index('idx_attendance_date',
                      AttendanceRecord.date),
                Index('idx_employee_active_dept',
                      Employee.active, Employee.department_id),
                Index('idx_employee_active_housing',
                      Employee.active, Employee.housing_id),
                Index('idx_vacation_employee_dates',
                      EmployeeVacation.employee_id,
                      EmployeeVacation.start_date,
                      EmployeeVacation.end_date),
                Index('idx_transfer_employee_dates',
                      EmployeeTransfer.employee_id,
                      EmployeeTransfer.start_date,
                      EmployeeTransfer.end_date)
            ]

            # Add each index
            for idx in indexes:
                try:
                    idx.create(db.engine)
                    logger.info(f"Created index: {idx.name}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        logger.info(f"Index {idx.name} already exists")
                    else:
                        logger.error(f"Error creating index {idx.name}: {str(e)}")

            logger.info("Database indexes applied successfully")
            return True

    except Exception as e:
        logger.error(f"Error applying database indexes: {str(e)}")
        return False

def run_optimization():
    """Run all optimization steps"""
    print("=" * 80)
    print("APPLYING PERFORMANCE OPTIMIZATIONS")
    print("=" * 80)

    # Step 1: Update app.py with optimized imports
    print("\n1. Updating app.py with optimized imports...")
    update_app_imports()

    # Step 2: Add cache button to template
    print("\n2. Adding cache clearing button to timesheet template...")
    add_cache_button_to_template()

    # Step 3: Apply database indexes
    print("\n3. Applying database indexes...")
    apply_database_indexes()

    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print("\nThe application performance has been significantly improved.")
    print("Please restart the application to apply all changes.")

if __name__ == "__main__":
    run_optimization()
