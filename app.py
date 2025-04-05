import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up database
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 15,
    "connect_args": {
        "sslmode": "require"
    }
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Also set environment variable for other modules to use
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Initialize the database
db.init_app(app)

# Import models after db initialization to avoid circular imports
with app.app_context():
    # Import models here
    from models import Department, Employee, AttendanceRecord, SyncLog, MonthPeriod
    db.create_all()
    
    # Initialize month periods if the table is empty
    if MonthPeriod.query.count() == 0:
        try:
            from initialize_months import initialize_month_periods
            initialize_month_periods()
            logger.info("Successfully initialized month periods")
        except Exception as e:
            logger.error(f"Error initializing month periods: {str(e)}")

# Import services after models
import data_processor
import sync_service

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Define route handlers
@app.route('/')
def index():
    """Home page showing dashboard overview"""
    return render_template('index.html')

@app.route('/timesheet')
def timesheet():
    """View monthly timesheet"""
    # Get query parameters
    year = request.args.get('year', data_processor.get_current_year())
    month = request.args.get('month', data_processor.get_current_month())
    dept_id = request.args.get('department', None)
    
    # Get departments for filter dropdown
    departments = Department.query.all()
    
    # Check if employees exist
    employee_count = Employee.query.count()
    logger.info(f"Total employees in database: {employee_count}")
    
    # Log attendance record count
    attendance_count = AttendanceRecord.query.count()
    logger.info(f"Total attendance records in database: {attendance_count}")
    
    # Process and format timesheet data
    try:
        timesheet_data = data_processor.generate_timesheet(year, month, dept_id)
        if timesheet_data.get('total_employees', 0) == 0:
            logger.warning(f"No employees found for timesheet: Year={year}, Month={month}, Dept={dept_id}")
    except Exception as e:
        logger.error(f"Error generating timesheet: {str(e)}")
        flash(f"Error generating timesheet: {str(e)}", "danger")
        timesheet_data = {
            'year': year,
            'month': month,
            'month_name': data_processor.get_month_name(int(month)),
            'dates': [],
            'employees': [],
            'total_employees': 0,
            'error': str(e)
        }
    
    return render_template('timesheet.html', 
                          timesheet_data=timesheet_data,
                          departments=departments,
                          selected_year=year,
                          selected_month=month,
                          selected_dept=dept_id)

@app.route('/departments')
def departments():
    """View and manage departments"""
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@app.route('/settings')
def settings():
    """Application settings"""
    # Get last sync information
    last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
    
    # Get current sync settings
    sync_settings = {
        'api_url': os.environ.get('BIOTIME_API_URL', sync_service.BIOTIME_API_BASE_URL),
        'username': os.environ.get('BIOTIME_USERNAME', sync_service.BIOTIME_USERNAME),
        'password': os.environ.get('BIOTIME_PASSWORD', sync_service.BIOTIME_PASSWORD),
        'interval': os.environ.get('SYNC_INTERVAL', '4'),
        'departments': os.environ.get('SYNC_DEPARTMENTS', ','.join(str(d) for d in sync_service.DEPARTMENTS))
    }
    
    return render_template('settings.html', last_sync=last_sync, sync_settings=sync_settings)

@app.route('/sync', methods=['POST'])
def trigger_sync():
    """Manually trigger data synchronization"""
    try:
        # Update sync settings if provided
        if 'biotime_url' in request.form:
            sync_service.BIOTIME_API_BASE_URL = request.form.get('biotime_url')
            os.environ['BIOTIME_API_URL'] = request.form.get('biotime_url')
            
        if 'biotime_username' in request.form:
            sync_service.BIOTIME_USERNAME = request.form.get('biotime_username')
            os.environ['BIOTIME_USERNAME'] = request.form.get('biotime_username')
            
        if 'biotime_password' in request.form and request.form.get('biotime_password') != '********':
            sync_service.BIOTIME_PASSWORD = request.form.get('biotime_password')
            os.environ['BIOTIME_PASSWORD'] = request.form.get('biotime_password')
            
        if 'sync_interval' in request.form and request.form.get('sync_interval'):
            interval = request.form.get('sync_interval')
            try:
                interval_hours = int(interval)
                os.environ['SYNC_INTERVAL'] = str(interval_hours)
                # Update scheduler if interval changed
                if scheduler.get_job('biotime_sync'):
                    scheduler.reschedule_job(
                        'biotime_sync', 
                        trigger='interval', 
                        hours=interval_hours
                    )
            except ValueError:
                flash('Sync interval must be a valid number', 'warning')
                
        if 'departments' in request.form and request.form.get('departments'):
            departments = request.form.get('departments')
            # Parse comma-separated department list
            try:
                dept_list = []
                for d in departments.split(','):
                    if d.strip().isdigit():
                        dept_list.append(int(d.strip()))
                
                if dept_list:  # Only update if at least one valid department ID
                    sync_service.DEPARTMENTS = dept_list
                    os.environ['SYNC_DEPARTMENTS'] = departments
                else:
                    flash('No valid department IDs provided, using default departments', 'warning')
            except Exception as e:
                flash(f'Error parsing departments: {str(e)}', 'warning')
                logger.error(f"Error parsing departments: {str(e)}")
            
        # Perform the data synchronization in a try-except block to handle potential errors
        try:
            with app.app_context():
                sync_service.sync_data(app)
            flash('Data synchronization started successfully!', 'success')
        except Exception as sync_e:
            logger.error(f"Sync process error: {str(sync_e)}")
            flash(f'Error during synchronization process: {str(sync_e)}', 'danger')
            
    except Exception as e:
        logger.error(f"Sync settings error: {str(e)}")
        flash(f'Error updating sync settings: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/save_settings', methods=['POST'])
def save_settings():
    """Save application settings"""
    try:
        # Update sync settings if provided
        if 'biotime_url' in request.form:
            url = request.form.get('biotime_url').strip()
            if url:
                sync_service.BIOTIME_API_BASE_URL = url
                os.environ['BIOTIME_API_URL'] = url
            
        if 'biotime_username' in request.form:
            username = request.form.get('biotime_username').strip()
            if username:
                sync_service.BIOTIME_USERNAME = username
                os.environ['BIOTIME_USERNAME'] = username
            
        if 'biotime_password' in request.form and request.form.get('biotime_password') != '********':
            password = request.form.get('biotime_password')
            if password:
                sync_service.BIOTIME_PASSWORD = password
                os.environ['BIOTIME_PASSWORD'] = password
            
        if 'sync_interval' in request.form and request.form.get('sync_interval'):
            interval = request.form.get('sync_interval').strip()
            try:
                interval_hours = int(interval)
                if interval_hours > 0:
                    os.environ['SYNC_INTERVAL'] = str(interval_hours)
                    # Update scheduler if interval changed
                    if scheduler.get_job('biotime_sync'):
                        scheduler.reschedule_job(
                            'biotime_sync', 
                            trigger='interval', 
                            hours=interval_hours
                        )
                else:
                    flash('Sync interval must be a positive number', 'warning')
            except ValueError:
                flash('Sync interval must be a valid number', 'warning')
                
        if 'departments' in request.form and request.form.get('departments'):
            departments = request.form.get('departments').strip()
            # Parse comma-separated department list
            try:
                dept_list = []
                for d in departments.split(','):
                    if d.strip().isdigit():
                        dept_list.append(int(d.strip()))
                
                if dept_list:  # Only update if at least one valid department ID
                    sync_service.DEPARTMENTS = dept_list
                    os.environ['SYNC_DEPARTMENTS'] = departments
                else:
                    flash('No valid department IDs provided, using default departments', 'warning')
            except Exception as dept_e:
                flash(f'Error parsing departments: {str(dept_e)}', 'warning')
                logger.error(f"Error parsing departments: {str(dept_e)}")
        
        # UI settings 
        ui_settings = {
            'default_view': request.form.get('default_view', 'current'),
            'weekend_days': request.form.getlist('weekend_days'),
            'present_color': request.form.get('present_color', '#ffffff'),
            'absent_color': request.form.get('absent_color', '#fbc6cb'),
            'vacation_color': request.form.get('vacation_color', '#fcffcc'),
            'transfer_color': request.form.get('transfer_color', '#b3ffb8'),
            'sick_color': request.form.get('sick_color', '#ffc107'),
            'eid_color': request.form.get('eid_color', '#0dcaf0')
        }
        
        # Additional checkboxes
        for setting in ['include_logo', 'include_legend', 'landscape_orientation']:
            ui_settings[setting] = 'on' if setting in request.form else 'off'
        
        # Save UI settings to session
        session['ui_settings'] = ui_settings
            
        flash('Settings saved successfully!', 'success')
        logger.info(f"Applying color settings: {ui_settings}")
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        flash(f'Error saving settings: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))
    
@app.route('/upload_sync', methods=['POST'])
def upload_sync():
    """Handle file upload for manual sync"""
    temp_path = None
    try:
        # Check if file was uploaded
        if 'sync_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('settings'))
            
        file = request.files['sync_file']
        
        # Check if file was selected
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('settings'))
            
        # Accept more file extensions (.txt, .csv, .tsv)
        allowed_extensions = ['.txt', '.csv', '.tsv']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash(f'Only {", ".join(allowed_extensions)} files are allowed', 'danger')
            return redirect(url_for('settings'))
            
        # Generate unique filename to avoid conflicts
        import uuid
        temp_filename = f'temp_sync_file_{uuid.uuid4().hex}{file_ext}'
        temp_path = os.path.join(os.getcwd(), temp_filename)
        
        # Save the file temporarily
        file.save(temp_path)
        logger.info(f"Saved uploaded file to {temp_path}")
        
        # Process file with sync service
        records = 0
        try:
            # Use a separate try-except block for processing to handle database errors
            with app.app_context():
                records = sync_service.process_uploaded_file(temp_path)
                
            if records > 0:
                flash(f'Successfully processed {records} records from uploaded file', 'success')
            else:
                flash('No records were processed from the uploaded file. Please check file format.', 'warning')
                
        except Exception as proc_e:
            logger.error(f"Error in file processing: {str(proc_e)}")
            flash(f'Error processing file data: {str(proc_e)}', 'danger')
            
    except Exception as e:
        logger.error(f"Error handling uploaded file: {str(e)}")
        flash(f'Error uploading file: {str(e)}', 'danger')
        
    finally:
        # Ensure temporary file is removed
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Removed temporary file {temp_path}")
        except Exception as cleanup_e:
            logger.error(f"Error removing temporary file: {str(cleanup_e)}")
        
    return redirect(url_for('settings'))

# Setup scheduled task for data synchronization
def initialize_scheduler():
    scheduler.add_job(
        sync_service.sync_data, 
        'interval', 
        hours=4, 
        id='biotime_sync',
        kwargs={'app': app}
    )
    scheduler.start()
    logger.info("Scheduler started - BioTime sync job scheduled every 4 hours")

# Add jinja template helper function
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    return dict(now=now)

# Start the scheduler with the app context
def start_scheduler():
    initialize_scheduler()

# Initialize scheduler when app is ready
with app.app_context():
    start_scheduler()

# Shutdown scheduler when app exits
import atexit
atexit.register(lambda: scheduler.shutdown())
