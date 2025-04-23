import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, g
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from database import db, init_db
from translations import get_text
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Biotime API URLs - primary and backup
BIOTIME_PRIMARY_API_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BIOTIME_BACKUP_API_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/"

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
init_db(app)

# Import models after db initialization to avoid circular imports
from models import Department, Employee, AttendanceRecord, SyncLog, MonthPeriod

# Import the AI module
from ai_analytics import BiometricAI

# Set up pre-request handlers for language
@app.before_request
def before_request():
    # Set default language if not in session
    if 'language' not in session:
        session['language'] = 'en'  # Default to English
    g.language = session.get('language', 'en')

# Add translation function to template context
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    
    def t(key):
        return get_text(key, g.language)
    
    def get_dir():
        return 'rtl' if g.language == 'ar' else 'ltr'
        
    return dict(now=now, t=t, get_dir=get_dir)

with app.app_context():
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

# Route to change language
@app.route('/change_language/<language>')
def change_language(language):
    """Change the display language"""
    if language in ['en', 'ar']:
        session['language'] = language
    
    # Redirect to the previous page or to the home page
    next_page = request.args.get('next') or request.referrer or url_for('index')
    return redirect(next_page)

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
    """Render settings page with current BiometricSync settings"""
    sync_settings = {
        'api_url': os.environ.get('BIOTIME_API_URL', 'http://172.16.16.13:8585/att/api/transactionReport/export/'),
        'username': os.environ.get('BIOTIME_USERNAME', 'raghad'),
        'password': '********',  # Never expose the actual password
        'interval': os.environ.get('SYNC_INTERVAL', '24'),
        'departments': os.environ.get('DEPARTMENTS', '10'),
        'start_date': os.environ.get('SYNC_START_DATE', ''),
        'end_date': os.environ.get('SYNC_END_DATE', ''),
        'language': session.get('language', 'en')  # Add language setting
    }
    
    # Get last sync information
    try:
        last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
    except Exception as e:
        app.logger.error(f"Error getting sync log: {str(e)}")
        last_sync = None
    
    return render_template('settings.html', sync_settings=sync_settings, last_sync=last_sync)

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
        
        # Handle date range settings
        if 'start_date' in request.form and request.form.get('start_date'):
            start_date = request.form.get('start_date').strip()
            os.environ['SYNC_START_DATE'] = start_date
            sync_service.SYNC_START_DATE = start_date
            logger.info(f"Updated sync start date: {start_date}")
            
        if 'end_date' in request.form and request.form.get('end_date'):
            end_date = request.form.get('end_date').strip()
            os.environ['SYNC_END_DATE'] = end_date
            sync_service.SYNC_END_DATE = end_date
            logger.info(f"Updated sync end date: {end_date}")
        
        # Handle language setting
        if 'language' in request.form and request.form.get('language') in ['en', 'ar']:
            language = request.form.get('language')
            session['language'] = language
            logger.info(f"Changed display language to: {language}")
        
        # UI settings - obtener configuración existente o crear nueva
        ui_settings = session.get('ui_settings', {})
        
        # Actualizar configuraciones de apariencia de la interfaz de usuario
        if 'weekend_days[]' in request.form:
            weekend_days = request.form.getlist('weekend_days[]')
            ui_settings['weekend_days'] = weekend_days
            logger.info(f"Updated weekend days to: {weekend_days}")
        else:
            # Default to Friday and Saturday
            ui_settings['weekend_days'] = ['4', '5']  # 4=Friday, 5=Saturday
            
        # Otras configuraciones UI 
        ui_fields = [
            'default_view', 'present_color', 'absent_color', 
            'vacation_color', 'transfer_color', 'sick_color', 'eid_color'
        ]
        
        for field in ui_fields:
            if field in request.form:
                ui_settings[field] = request.form.get(field)
        
        # Checkboxes adicionales
        for setting in ['include_logo', 'include_legend', 'landscape_orientation']:
            ui_settings[setting] = 'on' if setting in request.form else 'off'
        
        # Guardar configuraciones UI en la sesión
        session['ui_settings'] = ui_settings
            
        flash('Settings saved successfully!', 'success')
        logger.info(f"UI settings saved: {ui_settings}")
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
        flash(f"Error uploading file: {str(e)}", 'danger')
        
    finally:
        # Ensure temporary file is removed
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Removed temporary file {temp_path}")
        except Exception as cleanup_e:
            logger.error(f"Error removing temporary file: {str(cleanup_e)}")
        
    return redirect(url_for('settings'))

@app.route('/trigger_sync', methods=['POST'])
def trigger_sync():
    """Trigger a manual sync with BioTime"""
    try:
        # الحصول على تواريخ المزامنة من النموذج إذا تم تقديمها
        if 'start_date' in request.form and request.form.get('start_date', '').strip():
            start_date = request.form.get('start_date').strip()
            os.environ['SYNC_START_DATE'] = start_date
            sync_service.SYNC_START_DATE = start_date
            logger.info(f"تم تعيين تاريخ بداية المزامنة: {start_date}")
            
        if 'end_date' in request.form and request.form.get('end_date', '').strip():
            end_date = request.form.get('end_date').strip()
            os.environ['SYNC_END_DATE'] = end_date
            sync_service.SYNC_END_DATE = end_date
            logger.info(f"تم تعيين تاريخ نهاية المزامنة: {end_date}")
        
        # استخدام الوظيفة الجديدة للمزامنة في الخلفية
        if sync_service.start_sync_in_background(app=app):
            flash('تم بدء عملية المزامنة بنجاح.', 'info')
        else:
            flash('هناك عملية مزامنة جارية بالفعل.', 'warning')
    except Exception as e:
        logger.error(f"خطأ في بدء المزامنة: {str(e)}")
        flash(f"خطأ في بدء المزامنة: {str(e)}", 'danger')
    
    return redirect(url_for('settings'))

@app.route('/cancel_sync', methods=['POST'])
def cancel_sync():
    """إلغاء عملية المزامنة الجارية"""
    global SYNC_CANCELLATION_FLAG
    
    try:
        # تعيين علم الإلغاء إلى True
        SYNC_CANCELLATION_FLAG = True
        
        # البحث عن أحدث عملية مزامنة جارية
        last_sync = SyncLog.query.filter_by(status="in_progress").order_by(SyncLog.sync_time.desc()).first()
        
        # إذا وجدت عملية مزامنة جارية، قم بتحديث حالتها
        if last_sync:
            last_sync.status = "cancelled"
            last_sync.error_message = "تم إلغاء المزامنة بواسطة المستخدم"
            last_sync.end_time = datetime.utcnow()
            db.session.commit()
            
            flash("تم إلغاء عملية المزامنة بنجاح", "info")
        else:
            flash("لم يتم العثور على عملية مزامنة جارية", "warning")
            
    except Exception as e:
        logger.error(f"خطأ أثناء محاولة إلغاء المزامنة: {str(e)}")
        flash(f"حدث خطأ أثناء محاولة إلغاء المزامنة: {str(e)}", "danger")
    
    return redirect(url_for('settings'))

@app.route('/sync_results')
def sync_results():
    """Display sync results and attendance data"""
    try:
        # Get filter parameters
        department = request.args.get('department')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee = request.args.get('employee')
        page = int(request.args.get('page', 1))
        per_page = 50  # Number of records per page
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        
        # Build query for attendance records
        query = db.session.query(
            AttendanceRecord,
            Employee.name.label('employee_name'),
            Department.name.label('department_name')
        ).join(
            Employee, AttendanceRecord.employee_id == Employee.id
        ).join(
            Department, Employee.department_id == Department.id
        )
        
        # Apply filters
        if department:
            query = query.filter(Employee.department_id == department)
            
        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
            
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
            
        if employee:
            query = query.filter(Employee.name.ilike(f'%{employee}%'))
            
        # Order by date (newest first)
        query = query.order_by(AttendanceRecord.date.desc())
        
        # Count total records for pagination
        total_records = query.count()
        total_pages = (total_records + per_page - 1) // per_page
        
        # Paginate results
        records = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Format records for display
        attendance_records = []
        for record, emp_name, dept_name in records:
            # Get day of week in Arabic
            weekday = data_processor.get_day_name(record.date.weekday())
            
            attendance_records.append({
                'employee_name': emp_name,
                'department_name': dept_name,
                'date': record.date.strftime('%Y-%m-%d'),
                'weekday': weekday,
                'clock_in': record.clock_in.strftime('%H:%M') if record.clock_in else None,
                'clock_out': record.clock_out.strftime('%H:%M') if record.clock_out else None,
                'terminal_alias_in': record.terminal_alias_in,
                'terminal_alias_out': record.terminal_alias_out,
                'total_time': record.total_time,
                'attendance_status': record.attendance_status
            })
            
        # Get last sync info
        last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
        
        # Prepare sync data summary
        earliest_record = db.session.query(func.min(AttendanceRecord.date)).scalar()
        latest_record = db.session.query(func.max(AttendanceRecord.date)).scalar()
        records_count = AttendanceRecord.query.count()
        
        sync_data = {
            'records_count': records_count,
            'start_date': earliest_record.strftime('%Y-%m-%d') if earliest_record else 'N/A',
            'end_date': latest_record.strftime('%Y-%m-%d') if latest_record else 'N/A',
            'last_sync': last_sync.sync_time.strftime('%Y-%m-%d %H:%M:%S') if last_sync else 'Never'
        }
        
        # Pagination data
        pagination = {
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_records': total_records
        } if total_pages > 1 else None
        
        # Filter data for reuse in pagination links
        filter_data = {
            'department': department,
            'start_date': start_date,
            'end_date': end_date,
            'employee': employee
        }
        
        return render_template('sync_results.html',
                              sync_data=sync_data,
                              attendance_records=attendance_records,
                              departments=departments,
                              selected_dept=department,
                              filter_data=filter_data,
                              pagination=pagination)
    
    except Exception as e:
        logger.error(f"Error displaying sync results: {str(e)}")
        flash(f"Error displaying results: {str(e)}", "danger")
        return redirect(url_for('settings'))

# AI Analytics Routes
@app.route('/ai')
def ai_dashboard():
    """AI Analytics Dashboard"""
    # Get departments for filter dropdown
    departments = Department.query.all()
    
    # Get some initial statistics
    try:
        # Get recent attendance records (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        recent_records = AttendanceRecord.query.filter(
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        ).all()
        
        # Generate attendance chart for overall system
        attendance_chart = BiometricAI.generate_attendance_chart(days=30)
        
        # Get department statistics
        dept_stats = data_processor.get_department_stats()
        
        # Get AI recommendations
        recommendations = BiometricAI.provide_optimization_recommendations()
        
    except Exception as e:
        logger.error(f"Error preparing AI dashboard: {str(e)}")
        flash(f"Error loading AI analytics: {str(e)}", "danger")
        attendance_chart = None
        recommendations = []
        dept_stats = []
    
    return render_template('ai_dashboard.html', 
                          departments=departments,
                          attendance_chart=attendance_chart,
                          recommendations=recommendations,
                          dept_stats=dept_stats)

@app.route('/ai/anomalies')
def ai_anomalies():
    """Detect and display attendance anomalies"""
    try:
        # Get department filter
        dept_id = request.args.get('department', None)
        days = int(request.args.get('days', 30))
        
        # Get end date and start date
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Build query for attendance records
        query = AttendanceRecord.query.filter(
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        )
        
        if dept_id:
            # Get employees in department
            employee_ids = [e.id for e in Employee.query.filter_by(department_id=dept_id).all()]
            query = query.filter(AttendanceRecord.employee_id.in_(employee_ids))
        
        # Get attendance records
        attendance_records = query.all()
        
        # Detect anomalies
        anomalies = BiometricAI.detect_attendance_anomalies(attendance_records)
        
        # Organize anomalies by employee
        employees_map = {e.id: e for e in Employee.query.all()}
        organized_anomalies = []
        
        for anomaly in anomalies:
            emp_id = anomaly['employee_id']
            employee = employees_map.get(emp_id)
            
            if employee:
                organized_anomalies.append({
                    'employee_id': emp_id,
                    'employee_name': employee.name,
                    'date': anomaly['date'],
                    'anomaly_type': anomaly['anomaly_type'],
                    'details': anomaly
                })
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        selected_dept = Department.query.get(dept_id) if dept_id else None
        
        return render_template('ai_anomalies.html',
                               anomalies=organized_anomalies,
                               departments=departments,
                               selected_dept=selected_dept,
                               days=days,
                               start_date=start_date,
                               end_date=end_date)
    
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
        flash(f"Error detecting anomalies: {str(e)}", "danger")
        return redirect(url_for('ai_dashboard'))

@app.route('/ai/predictions')
def ai_predictions():
    """Generate and display attendance predictions"""
    try:
        # Get department filter
        dept_id = request.args.get('department', None)
        days = int(request.args.get('days', 7))
        
        if dept_id:
            # Generate forecast for department
            forecast = BiometricAI.generate_attendance_forecast(int(dept_id), days)
        else:
            # If no department selected, just provide empty forecast
            forecast = {'forecast': [], 'message': 'Please select a department'}
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        selected_dept = Department.query.get(dept_id) if dept_id else None
        
        return render_template('ai_predictions.html',
                               forecast=forecast,
                               departments=departments,
                               selected_dept=selected_dept,
                               days=days)
    
    except Exception as e:
        logger.error(f"Error generating predictions: {str(e)}")
        flash(f"Error generating predictions: {str(e)}", "danger")
        return redirect(url_for('ai_dashboard'))

@app.route('/ai/patterns')
def ai_patterns():
    """Identify and display attendance patterns"""
    try:
        # Get filters
        dept_id = request.args.get('department', None)
        emp_id = request.args.get('employee', None)
        
        # Get patterns based on filters
        if emp_id:
            patterns = BiometricAI.identify_attendance_patterns(employee_id=int(emp_id))
            employee = Employee.query.get(emp_id)
            title = f"Attendance Patterns for {employee.name}" if employee else "Employee Attendance Patterns"
        elif dept_id:
            patterns = BiometricAI.identify_attendance_patterns(department_id=int(dept_id))
            department = Department.query.get(dept_id)
            title = f"Attendance Patterns for {department.name} Department" if department else "Department Attendance Patterns"
        else:
            patterns = {'message': 'Please select a department or employee'}
            title = "Attendance Patterns"
        
        # Get departments and employees for filter dropdowns
        departments = Department.query.all()
        employees = []
        
        if dept_id:
            employees = Employee.query.filter_by(department_id=int(dept_id)).all()
        
        return render_template('ai_patterns.html',
                               patterns=patterns,
                               title=title,
                               departments=departments,
                               employees=employees,
                               selected_dept=dept_id,
                               selected_emp=emp_id)
    
    except Exception as e:
        logger.error(f"Error analyzing patterns: {str(e)}")
        flash(f"Error analyzing patterns: {str(e)}", "danger")
        return redirect(url_for('ai_dashboard'))

@app.route('/ai/clustering')
def ai_clustering():
    """Cluster employees based on attendance patterns"""
    try:
        # Get department filter
        dept_id = request.args.get('department', None)
        
        # Perform clustering based on filter
        if dept_id:
            clustering_results = BiometricAI.cluster_employees_by_attendance(department_id=int(dept_id))
            department = Department.query.get(dept_id)
            title = f"Employee Clustering for {department.name} Department" if department else "Department Employee Clustering"
        else:
            clustering_results = BiometricAI.cluster_employees_by_attendance()
            title = "Overall Employee Clustering"
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        
        return render_template('ai_clustering.html',
                               clustering_results=clustering_results,
                               title=title,
                               departments=departments,
                               selected_dept=dept_id)
    
    except Exception as e:
        logger.error(f"Error clustering employees: {str(e)}")
        flash(f"Error clustering employees: {str(e)}", "danger")
        return redirect(url_for('ai_dashboard'))

@app.route('/ai/recommendations')
def ai_recommendations():
    """Display AI-generated optimization recommendations"""
    try:
        # Get department filter
        dept_id = request.args.get('department', None)
        
        # Get recommendations based on filter
        if dept_id:
            recommendations = BiometricAI.provide_optimization_recommendations(department_id=int(dept_id))
            department = Department.query.get(dept_id)
            title = f"Recommendations for {department.name} Department" if department else "Department Recommendations"
        else:
            recommendations = BiometricAI.provide_optimization_recommendations()
            title = "System-wide Recommendations"
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        
        return render_template('ai_recommendations.html',
                               recommendations=recommendations,
                               title=title,
                               departments=departments,
                               selected_dept=dept_id)
    
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        flash(f"Error generating recommendations: {str(e)}", "danger")
        return redirect(url_for('ai_dashboard'))

@app.route('/api/ai/chart')
def api_ai_chart():
    """API endpoint to generate attendance charts"""
    try:
        dept_id = request.args.get('department')
        emp_id = request.args.get('employee')
        days = int(request.args.get('days', 30))
        
        if emp_id:
            chart_data = BiometricAI.generate_attendance_chart(employee_id=int(emp_id), days=days)
        elif dept_id:
            chart_data = BiometricAI.generate_attendance_chart(department_id=int(dept_id), days=days)
        else:
            chart_data = BiometricAI.generate_attendance_chart(days=days)
        
        return jsonify({'chart': chart_data})
    
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_sync_status')
def check_sync_status():
    """API endpoint to check the current sync status for real-time updates"""
    try:
        # استخدام النظام الجديد لتتبع حالة المزامنة
        sync_status = sync_service.get_sync_status()
        
        # إذا كانت المزامنة غير نشطة، نتحقق من آخر سجل مزامنة
        if sync_status["status"] == "none":
            last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
            
            if last_sync:
                return jsonify({
                    'status': last_sync.status,
                    'message': f'آخر مزامنة: {last_sync.sync_time.strftime("%Y-%m-%d %H:%M:%S")}',
                    'records': last_sync.records_synced,
                    'sync_time': last_sync.sync_time.isoformat(),
                    'error': last_sync.error_message
                })
            else:
                return jsonify({
                    'status': 'none',
                    'message': 'لم يتم العثور على أي سجل مزامنة'
                })
        
        # إذا كانت المزامنة نشطة (in_progress)
        if sync_status["status"] == "in_progress":
            return jsonify({
                'status': 'in_progress',
                'message': 'المزامنة جارية...',
                'step': sync_status["step"],
                'progress': sync_status["progress"],
                'progress_message': sync_status["message"],
                'can_cancel': True
            })
        
        # حالات المزامنة الأخرى (success, error, cancelled)
        return jsonify({
            'status': sync_status["status"],
            'message': sync_status["message"],
            'records': sync_status["records"],
            'error': sync_status["error"]
        })
    
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة المزامنة: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ أثناء التحقق من حالة المزامنة',
            'error': str(e)
        })

@app.route('/api/employees/department/<int:dept_id>')
def api_get_employees_by_department(dept_id):
    """API endpoint to fetch employees by department"""
    try:
        employees = Employee.query.filter_by(department_id=dept_id).all()
        employee_list = []
        
        for employee in employees:
            employee_list.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'profession': employee.profession or '',
                'daily_hours': employee.daily_hours,
                'active': employee.active
            })
        
        return jsonify({
            'success': True,
            'employees': employee_list
        })
    
    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/employees/<int:employee_id>', methods=['GET'])
def api_get_employee(employee_id):
    """API endpoint to get a single employee's details"""
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Employee not found'
            }), 404
        
        return jsonify({
            'success': True,
            'employee': {
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'profession': employee.profession or '',
                'daily_hours': employee.daily_hours,
                'active': employee.active,
                'department_id': employee.department_id
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching employee: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
def api_update_employee(employee_id):
    """API endpoint to update an employee's details"""
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'error': 'Employee not found'
            }), 404
        
        # Get JSON data from request
        data = request.json
        
        # Update employee fields
        if 'name' in data:
            employee.name = data['name']
        
        if 'profession' in data:
            employee.profession = data['profession']
        
        if 'daily_hours' in data:
            try:
                employee.daily_hours = float(data['daily_hours'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Daily hours must be a valid number'
                }), 400
        
        if 'active' in data:
            employee.active = data['active']
        
        # Save changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Employee updated successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating employee: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Setup scheduled task for data synchronization
def initialize_scheduler():
    scheduler.add_job(
        sync_service.simple_sync_data,  # Usar la función simple_sync_data en lugar de sync_data
        'interval', 
        hours=4, 
        id='biotime_sync',
        kwargs={'app': app}
    )
    scheduler.start()
    logger.info("Scheduler started - BioTime sync job scheduled every 4 hours")

# Start the scheduler with the app context
def start_scheduler():
    initialize_scheduler()

# Initialize scheduler when app is ready
with app.app_context():
    start_scheduler()

# Shutdown scheduler when app exits
import atexit
atexit.register(lambda: scheduler.shutdown())

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)