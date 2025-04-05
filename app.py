import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
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
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///attendance.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
    
    # Process and format timesheet data
    timesheet_data = data_processor.generate_timesheet(year, month, dept_id)
    
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
            
        if 'sync_interval' in request.form:
            interval = request.form.get('sync_interval')
            os.environ['SYNC_INTERVAL'] = interval
            # Update scheduler if interval changed
            if scheduler.get_job('biotime_sync'):
                scheduler.reschedule_job(
                    'biotime_sync', 
                    trigger='interval', 
                    hours=int(interval)
                )
                
        if 'departments' in request.form:
            departments = request.form.get('departments')
            # Parse comma-separated department list
            sync_service.DEPARTMENTS = [int(d.strip()) for d in departments.split(',') if d.strip().isdigit()]
            os.environ['SYNC_DEPARTMENTS'] = departments
            
        with app.app_context():
            sync_service.sync_data()
        flash('Data synchronization started successfully!', 'success')
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        flash(f'Error during synchronization: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/save_settings', methods=['POST'])
def save_settings():
    """Save application settings"""
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
            
        if 'sync_interval' in request.form:
            interval = request.form.get('sync_interval')
            os.environ['SYNC_INTERVAL'] = interval
            # Update scheduler if interval changed
            if scheduler.get_job('biotime_sync'):
                scheduler.reschedule_job(
                    'biotime_sync', 
                    trigger='interval', 
                    hours=int(interval)
                )
                
        if 'departments' in request.form:
            departments = request.form.get('departments')
            # Parse comma-separated department list
            sync_service.DEPARTMENTS = [int(d.strip()) for d in departments.split(',') if d.strip().isdigit()]
            os.environ['SYNC_DEPARTMENTS'] = departments
            
        flash('Settings saved successfully!', 'success')
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        flash(f'Error saving settings: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))
    
@app.route('/upload_sync', methods=['POST'])
def upload_sync():
    """Handle file upload for manual sync"""
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
            
        # Check if file has allowed extension
        if not file.filename.endswith('.txt'):
            flash('Only .txt files are allowed', 'danger')
            return redirect(url_for('settings'))
            
        # Save the file temporarily
        temp_path = os.path.join(os.getcwd(), 'temp_sync_file.txt')
        file.save(temp_path)
        
        # Process file with sync service
        with app.app_context():
            records = sync_service.process_uploaded_file(temp_path)
            
        # Remove temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if records > 0:
            flash(f'Successfully processed {records} records from uploaded file', 'success')
        else:
            flash('No records were processed from the uploaded file', 'warning')
            
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        flash(f'Error processing uploaded file: {str(e)}', 'danger')
        
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
