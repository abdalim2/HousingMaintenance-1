import os
import logging
import threading
import sys
import io
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, g
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from database import db, init_db
from translations import get_text
from sqlalchemy import func

# Configure system encoding for Arabic text
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging with proper encoding
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
# Ensure Flask properly handles UTF-8
app.config['JSON_AS_ASCII'] = False  # Allow JSON to contain non-ASCII characters

# Add utility function for terminal output with Arabic support
def log_with_arabic(message):
    """Log messages with proper Arabic encoding"""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        # Fallback if console doesn't support Unicode
        safe_message = message.encode('utf-8', errors='replace').decode('utf-8')
        logger.info(f"(Encoded message): {safe_message}")

# Biotime API URLs - primary and backup
BIOTIME_PRIMARY_API_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"
BIOTIME_BACKUP_API_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/"

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 1800,  # تدوير الاتصالات كل 30 دقيقة بدلاً من 5 دقائق
    "pool_pre_ping": True,  # للتحقق من أن الاتصال لا يزال صالحاً
    "pool_size": 25,  # زيادة حجم تجمّع الاتصالات
    "max_overflow": 25,  # زيادة الحد الأقصى للاتصالات الإضافية
    "pool_timeout": 30,  # زيادة وقت انتظار الاتصال
    "pool_use_lifo": True,  # استخدام LIFO للحصول على اتصالات أسرع
    "connect_args": {
        "sslmode": "require",
        "keepalives": 1,  # تفعيل الاتصالات المستمرة
        "keepalives_idle": 60,  # الوقت بالثواني قبل إرسال حزمة keepalive
        "keepalives_interval": 10  # الفاصل الزمني بين محاولات keepalive
    }
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # تعطيل تتبع التعديلات لتحسين الأداء
app.config["SQLALCHEMY_ECHO"] = False  # تعطيل طباعة استعلامات SQL لتحسين الأداء

# Also set environment variable for other modules to use
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Initialize the database
init_db(app)

# Import models after db initialization to avoid circular imports
from models import Department, Employee, AttendanceRecord, SyncLog, MonthPeriod, Housing, BiometricTerminal, EmployeeVacation, EmployeeTransfer

# Import the AI module
from ai_analytics import BiometricAI

# تعديل المتغير العام لتعطيل وضع البيانات التجريبية
MOCK_MODE_ENABLED = False

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
    """Homepage with dashboard"""
    # Get housing stats for dashboard
    housing_stats = data_processor.get_housing_stats()
    
    # Get department stats
    dept_stats = data_processor.get_department_stats()
    
    # Get sync status for display
    sync_status = sync_service.get_sync_status()
    last_sync = None
    
    try:
        last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
    except Exception:
        pass
    
    # Get attendance statistics for the last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    present_count = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date,
        AttendanceRecord.attendance_status == 'P'
    ).count()
    
    absent_count = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date,
        AttendanceRecord.attendance_status == 'A'
    ).count()
    
    vacation_count = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date,
        AttendanceRecord.attendance_status == 'V'
    ).count()
    
    # Calculate attendance percentage
    total_records = present_count + absent_count + vacation_count
    attendance_pct = round((present_count / total_records) * 100, 1) if total_records > 0 else 0
      # Get total employees count
    employee_count = Employee.query.count()
    
    # Get active terminals count
    active_terminals = BiometricTerminal.query.count()
    
    # Get recent records
    recent_records = AttendanceRecord.query.order_by(
        AttendanceRecord.date.desc(), 
        AttendanceRecord.clock_in.desc()
    ).limit(10).all()
    
    return render_template(
        'index.html',
        housing_stats=housing_stats,
        dept_stats=dept_stats,
        employee_count=employee_count,
        terminals_count=active_terminals,
        attendance_pct=attendance_pct,
        present_count=present_count,
        absent_count=absent_count,
        vacation_count=vacation_count,
        recent_records=recent_records,
        sync_status=sync_status,
        last_sync=last_sync,
        mock_mode_enabled=False  # تعديل لعدم استخدام البيانات التجريبية
    )

@app.route('/dashboard/ar')
def arabic_dashboard():
    """Arabic version of the dashboard"""
    session['language'] = 'ar'  # Set language to Arabic
    return render_template('dashboard_ar.html')

@app.route('/timesheet')
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
    
    # Get departments and housings for filter dropdown
    departments = Department.query.all()
    housings = Housing.query.all()  # جديد: قائمة المساكن للتصفية
    
    # Get month configuration periods
    month_dates = {}
    try:
        month_periods = MonthPeriod.query.all()
        for period in month_periods:
            # Extract the month from month_code (format: MM/YY)
            month_num = int(period.month_code.split('/')[0]) if period.month_code else 0
            
            month_dates[month_num] = {
                'start': period.start_date.strftime('%Y-%m-%d') if period.start_date else None,
                'end': period.end_date.strftime('%Y-%m-%d') if period.end_date else None
            }
        logger.info(f"Loaded {len(month_dates)} month configurations")
    except Exception as e:
        logger.error(f"Error loading month configurations: {str(e)}")
        month_dates = {}
    
    # Check if employees exist
    try:
        # Only select columns that definitely exist to avoid the housing_id error
        employee_count = db.session.query(db.func.count(Employee.id)).scalar()
        logger.info(f"Total employees in database: {employee_count}")
        
        # Log attendance record count
        attendance_count = AttendanceRecord.query.count()
        logger.info(f"Total attendance records in database: {attendance_count}")
    except Exception as e:
        logger.error(f"Error checking database counts: {str(e)}")
        employee_count = 0
        attendance_count = 0
    
    # If custom start/end dates are provided, use them
    # Otherwise, check if month configuration exists for the selected month
    if not start_date and not end_date and int(month) in month_dates:
        month_config = month_dates[int(month)]
        start_date = month_config.get('start')
        end_date = month_config.get('end')
        logger.info(f"Using configured dates for month {month}: {start_date} to {end_date}")
    
    # Process and format timesheet data
    try:
        timesheet_data = data_processor.generate_timesheet(year, month, dept_id, start_date, end_date, housing_id)
        if timesheet_data.get('total_employees', 0) == 0:
            logger.warning(f"No employees found for timesheet: Year={year}, Month={month}, Dept={dept_id}, Housing={housing_id}")
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
                          housings=housings,  # جديد: إرسال قائمة المساكن إلى القالب
                          selected_year=year,
                          selected_month=month,
                          selected_dept=dept_id,
                          selected_housing=housing_id,  # جديد: معرف السكن المحدد
                          month_dates=month_dates)

@app.route('/departments')
def departments():
    """View and manage departments"""
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@app.route('/add_department', methods=['POST'])
def add_department():
    """Add a new department"""
    try:
        name = request.form.get('department_name')
        biotime_id = request.form.get('biotime_id')
        
        if not name or not biotime_id:
            flash('اسم القسم ومعرف النظام مطلوبان', 'danger')
            return redirect(url_for('departments'))
        
        # Check if department already exists with this name or ID
        existing_dept = Department.query.filter((Department.name == name) | 
                                             (Department.biotime_id == biotime_id)).first()
        if existing_dept:
            flash('يوجد قسم بنفس الاسم أو رقم المعرف', 'danger')
            return redirect(url_for('departments'))
        
        new_department = Department(
            name=name,
            biotime_id=biotime_id,
            active=True
        )
        
        db.session.add(new_department)
        db.session.commit()
        
        flash('تمت إضافة القسم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding department: {str(e)}")
        flash(f'حدث خطأ أثناء إضافة القسم: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/edit_department', methods=['POST'])
def edit_department():
    """Edit existing department"""
    try:
        dept_id = request.form.get('department_id')
        name = request.form.get('department_name')
        biotime_id = request.form.get('biotime_id')
        active = request.form.get('active') == 'on'
        
        if not dept_id or not name or not biotime_id:
            flash('معرف واسم القسم ومعرف النظام مطلوبة', 'danger')
            return redirect(url_for('departments'))
        
        department = Department.query.get(dept_id)
        if not department:
            flash('لم يتم العثور على القسم', 'danger')
            return redirect(url_for('departments'))
        
        # Check if another department has this name or ID
        existing_dept = Department.query.filter(
            ((Department.name == name) | (Department.biotime_id == biotime_id)) & 
            (Department.id != department.id)
        ).first()
        
        if existing_dept:
            flash('يوجد قسم آخر بنفس الاسم أو رقم المعرف', 'danger')
            return redirect(url_for('departments'))
        
        department.name = name
        department.biotime_id = biotime_id
        department.active = active
        
        db.session.commit()
        
        flash('تم تحديث القسم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating department: {str(e)}")
        flash(f'حدث خطأ أثناء تحديث القسم: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/delete_department', methods=['POST'])
def delete_department():
    """Delete department"""
    try:
        dept_id = request.form.get('department_id')
        
        if not dept_id:
            flash('معرف القسم مطلوب', 'danger')
            return redirect(url_for('departments'))
        
        department = Department.query.get(dept_id)
        if not department:
            flash('لم يتم العثور على القسم', 'danger')
            return redirect(url_for('departments'))
        
        # Check if there are employees in this department
        employees_count = Employee.query.filter_by(department_id=dept_id).count()
        if employees_count > 0:
            flash(f'لا يمكن حذف القسم لأنه يحتوي على {employees_count} موظف. قم بنقل الموظفين أولاً.', 'warning')
            return redirect(url_for('departments'))
        
        db.session.delete(department)
        db.session.commit()
        
        flash('تم حذف القسم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting department: {str(e)}")
        flash(f'حدث خطأ أثناء حذف القسم: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/employee_status')
def employee_status():
    """Render employee status management page with pagination for better performance"""
    try:
        # Get page numbers from query parameters
        vacation_page = request.args.get('v_page', 1, type=int)
        transfer_page = request.args.get('t_page', 1, type=int)
        page_size = 25  # Number of records per page
        
        # Get filter parameters
        employee_id = request.args.get('employee_id', type=int)
        department_id = request.args.get('department_id', type=int)
        
        # Get all active employees for dropdown selection
        employees = Employee.query.filter_by(active=True).order_by(Employee.name).all()
        
        # Get all departments and housings for dropdown selection
        departments = Department.query.all()
        housings = Housing.query.all()
        
        # Base query for vacations with filtering
        vacation_query = db.session.query(EmployeeVacation)\
            .join(Employee, Employee.id == EmployeeVacation.employee_id)\
            .filter(Employee.active == True)
            
        # Base query for transfers with filtering
        transfer_query = db.session.query(EmployeeTransfer)\
            .join(Employee, Employee.id == EmployeeTransfer.employee_id)\
            .filter(Employee.active == True)
        
        # Apply filters if provided
        if employee_id:
            vacation_query = vacation_query.filter(EmployeeVacation.employee_id == employee_id)
            transfer_query = transfer_query.filter(EmployeeTransfer.employee_id == employee_id)
            
        if department_id:
            vacation_query = vacation_query.join(
                Employee, Employee.id == EmployeeVacation.employee_id
            ).filter(Employee.department_id == department_id)
            transfer_query = transfer_query.join(
                Employee, Employee.id == EmployeeTransfer.employee_id
            ).filter(Employee.department_id == department_id)
        
        # Get paginated results
        vacation_pagination = vacation_query.order_by(
            EmployeeVacation.start_date.desc()
        ).paginate(page=vacation_page, per_page=page_size, error_out=False)
        
        transfer_pagination = transfer_query.order_by(
            EmployeeTransfer.start_date.desc()
        ).paginate(page=transfer_page, per_page=page_size, error_out=False)
        
        # Get the records for the current page
        vacations = vacation_pagination.items
        transfers = transfer_pagination.items
        
        # Get counts for display
        vacation_count = vacation_query.count()
        transfer_count = transfer_query.count()
        
        return render_template('employee_status.html',
                              employees=employees,
                              departments=departments,
                              housings=housings,
                              vacations=vacations,
                              transfers=transfers,
                              vacation_pagination=vacation_pagination,
                              transfer_pagination=transfer_pagination,
                              vacation_count=vacation_count,
                              transfer_count=transfer_count,
                              selected_employee_id=employee_id,
                              selected_department_id=department_id)
    
    except Exception as e:
        logger.error(f"Error loading employee status page: {str(e)}")
        flash(f'حدث خطأ أثناء تحميل صفحة حالة الموظفين: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/save_vacation', methods=['POST'])
def save_vacation():
    """Save vacation data"""
    try:
        # Get form data
        vacation_id = request.form.get('id')
        employee_id = request.form.get('employee_id')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        notes = request.form.get('notes')
        
        # Validate date range
        if end_date < start_date:
            flash('End date cannot be earlier than start date', 'danger')
            return redirect(url_for('employee_status'))
        
        if vacation_id:
            # Update existing vacation
            vacation = EmployeeVacation.query.get(vacation_id)
            if not vacation:
                flash('Vacation record not found', 'danger')
                return redirect(url_for('employee_status'))
                
            vacation.employee_id = employee_id
            vacation.start_date = start_date
            vacation.end_date = end_date
            vacation.notes = notes
            flash('Vacation updated successfully', 'success')
        else:
            # Create new vacation
            vacation = EmployeeVacation(
                employee_id=employee_id,
                start_date=start_date,
                end_date=end_date,
                notes=notes
            )
            db.session.add(vacation)
            flash('Vacation added successfully', 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving vacation: {str(e)}', 'danger')
        app.logger.error(f'Error saving vacation: {str(e)}')
    
    return redirect(url_for('employee_status'))

@app.route('/save_transfer', methods=['POST'])
def save_transfer():
    """Save transfer data"""
    try:
        # Get form data
        transfer_id = request.form.get('id')
        employee_id = request.form.get('employee_id')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        transfer_type = request.form.get('transfer_type')
        notes = request.form.get('notes')
        
        # Transfer details based on type
        from_department_id = None
        to_department_id = None
        from_housing_id = None
        to_housing_id = None
        
        if transfer_type == 'department':
            from_department_id = request.form.get('from_department_id') or None
            to_department_id = request.form.get('to_department_id') or None
            
            # Update employee's department if to_department_id is set
            if to_department_id:
                employee = Employee.query.get(employee_id)
                if employee:
                    employee.department_id = to_department_id
        else:
            from_housing_id = request.form.get('from_housing_id') or None
            to_housing_id = request.form.get('to_housing_id') or None
            
            # Update employee's housing if to_housing_id is set
            if to_housing_id:
                employee = Employee.query.get(employee_id)
                if employee:
                    employee.housing_id = to_housing_id
        
        # Validate date range
        if end_date < start_date:
            flash('End date cannot be earlier than start date', 'danger')
            return redirect(url_for('employee_status'))
        
        if transfer_id:
            # Update existing transfer
            transfer = EmployeeTransfer.query.get(transfer_id)
            if not transfer:
                flash('Transfer record not found', 'danger')
                return redirect(url_for('employee_status'))
                
            transfer.employee_id = employee_id
            transfer.start_date = start_date
            transfer.end_date = end_date
            transfer.from_department_id = from_department_id
            transfer.to_department_id = to_department_id
            transfer.from_housing_id = from_housing_id
            transfer.to_housing_id = to_housing_id
            transfer.notes = notes
            flash('Transfer updated successfully', 'success')
        else:
            # Create new transfer
            transfer = EmployeeTransfer(
                employee_id=employee_id,
                start_date=start_date,
                end_date=end_date,
                from_department_id=from_department_id,
                to_department_id=to_department_id,
                from_housing_id=from_housing_id,
                to_housing_id=to_housing_id,
                notes=notes
            )
            db.session.add(transfer)
            flash('Transfer added successfully', 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving transfer: {str(e)}', 'danger')
        app.logger.error(f'Error saving transfer: {str(e)}')
    
    return redirect(url_for('employee_status'))

@app.route('/get_vacation/<int:id>')
def get_vacation(id):
    """Get vacation data as JSON"""
    vacation = EmployeeVacation.query.get_or_404(id)
    
    return jsonify({
        'id': vacation.id,
        'employee_id': vacation.employee_id,
        'start_date': vacation.start_date.strftime('%Y-%m-%d'),
        'end_date': vacation.end_date.strftime('%Y-%m-%d'),
        'notes': vacation.notes or ''
    })

@app.route('/get_transfer/<int:id>')
def get_transfer(id):
    """Get transfer data as JSON"""
    transfer = EmployeeTransfer.query.get_or_404(id)
    
    return jsonify({
        'id': transfer.id,
        'employee_id': transfer.employee_id,
        'start_date': transfer.start_date.strftime('%Y-%m-%d'),
        'end_date': transfer.end_date.strftime('%Y-%m-%d'),
        'from_department_id': transfer.from_department_id,
        'to_department_id': transfer.to_department_id,
        'from_housing_id': transfer.from_housing_id,
        'to_housing_id': transfer.to_housing_id,
        'notes': transfer.notes or ''
    })

@app.route('/delete_vacation/<int:id>')
def delete_vacation(id):
    """Delete a vacation record"""
    try:
        vacation = EmployeeVacation.query.get_or_404(id)
        db.session.delete(vacation)
        db.session.commit()
        flash('Vacation deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting vacation: {str(e)}', 'danger')
        app.logger.error(f'Error deleting vacation: {str(e)}')
    
    return redirect(url_for('employee_status'))

@app.route('/delete_transfer/<int:id>')
def delete_transfer(id):
    """Delete a transfer record"""
    try:
        transfer = EmployeeTransfer.query.get_or_404(id)
        db.session.delete(transfer)
        db.session.commit()
        flash('Transfer deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting transfer: {str(e)}', 'danger')
        app.logger.error(f'Error deleting transfer: {str(e)}')
    
    return redirect(url_for('employee_status'))

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
    
    # Get housings and biometric terminals for settings page
    try:
        housings = Housing.query.all()
        terminals = BiometricTerminal.query.all()
    except Exception as e:
        app.logger.error(f"Error fetching housings and terminals: {str(e)}")
        housings = []
        terminals = []
    
    # Check if mock mode is enabled
    mock_mode_enabled = os.environ.get("MOCK_MODE", "false").lower() == "true" or sync_service.MOCK_MODE_ENABLED
    
    return render_template('settings.html', 
                          sync_settings=sync_settings, 
                          last_sync=last_sync,
                          housings=housings,
                          terminals=terminals,
                          mock_mode_enabled=mock_mode_enabled)

@app.route('/trigger_sync', methods=['GET', 'POST'])
def trigger_sync():
    """Trigger a manual data synchronization with the biometric system"""
    try:
        # Get start and end dates from request parameters
        start_date = request.args.get('start_date') or request.form.get('start_date')
        end_date = request.args.get('end_date') or request.form.get('end_date')
        
        # Store selected dates in environment variables for sync service
        if start_date:
            os.environ['SYNC_START_DATE'] = start_date
            sync_service.SYNC_START_DATE = start_date
            logger.info(f"Using specified start date for sync: {start_date}")
            
        if end_date:
            os.environ['SYNC_END_DATE'] = end_date
            sync_service.SYNC_END_DATE = end_date
            logger.info(f"Using specified end date for sync: {end_date}")
        
        # Check if mock mode is requested (can be enabled via query parameter or form data)
        use_mock = request.args.get('mock') == 'true' or request.form.get('mock') == 'true'
        
        if use_mock:
            # Enable mock mode only if specifically requested
            os.environ['MOCK_MODE'] = "true"
            sync_service.MOCK_MODE_ENABLED = True
            logger.info("Mock mode enabled for sync at user request")
        else:
            # Disable mock mode to use the real API
            os.environ['MOCK_MODE'] = "false"
            sync_service.MOCK_MODE_ENABLED = False
            logger.info("Using real BioTime API for synchronization")
            
        # Use the start_sync_in_background function if available
        if hasattr(sync_service, 'start_sync_in_background'):
            # Modified method that doesn't rely on request context
            result = sync_service.start_sync_in_background(app=app)
            
            if result:
                flash('Data synchronization started successfully', 'success')
            else:
                flash('Failed to start synchronization - another sync may be running', 'warning')
        else:
            # Fall back to direct sync, passing dates explicitly
            thread = threading.Thread(
                target=sync_service.simple_sync_data,
                kwargs={
                    'app': app,
                    'request_start_date': start_date,
                    'request_end_date': end_date
                }
            )
            thread.daemon = True
            thread.start()
            flash('Data synchronization started successfully', 'success')
            
    except Exception as e:
        logger.error(f"Error triggering sync: {str(e)}")
        flash(f'Error triggering sync: {str(e)}', 'danger')
    
    # Redirect back to the previous page or settings
    next_page = request.args.get('next') or request.referrer or url_for('settings')
    return redirect(next_page)

@app.route('/reset_attendance_data', methods=['POST'])
def reset_attendance_data():
    """حذف بيانات الدوامات من قاعدة البيانات وإعادة المزامنة"""
    try:
        # التحقق من وجود تأكيد من المستخدم
        confirmation = request.form.get('confirmation')
        if confirmation != 'CONFIRM_DELETE':
            flash('يرجى تأكيد الحذف بكتابة CONFIRM_DELETE في مربع التأكيد', 'warning')
            return redirect(url_for('settings'))
            
        # حذف سجلات الدوام من قاعدة البيانات
        deleted_count = AttendanceRecord.query.delete()
        
        # حذف سجلات المزامنة السابقة 
        sync_logs_count = SyncLog.query.delete()
        
        # حفظ التغييرات في قاعدة البيانات
        db.session.commit()
        
        logger.info(f"تم حذف {deleted_count} سجل دوام و {sync_logs_count} سجل مزامنة")
        flash(f'تم حذف {deleted_count} سجل دوام و {sync_logs_count} سجل مزامنة بنجاح', 'success')
        
        # تشغيل المزامنة بعد الحذف إذا طلب المستخدم ذلك
        if request.form.get('sync_after_delete') == 'on':
            # تشغيل المزامنة في الخلفية
            if hasattr(sync_service, 'start_sync_in_background'):
                result = sync_service.start_sync_in_background(app=app)
                
                if result:
                    flash('تم بدء عملية المزامنة بعد حذف البيانات', 'info')
                else:
                    flash('فشلت عملية المزامنة - قد تكون هناك عملية أخرى جارية', 'warning')
            else:
                thread = threading.Thread(
                    target=sync_service.simple_sync_data,
                    kwargs={'app': app}
                )
                thread.daemon = True
                thread.start()
                flash('تم بدء عملية المزامنة بعد حذف البيانات', 'info')
        
    except Exception as e:
        # إلغاء التغييرات في حالة حدوث خطأ
        db.session.rollback()
        logger.error(f"خطأ أثناء حذف بيانات الدوام: {str(e)}")
        flash(f'حدث خطأ أثناء حذف البيانات: {str(e)}', 'danger')
    
    # إعادة توجيه المستخدم إلى صفحة الإعدادات
    return redirect(url_for('settings'))

@app.route('/add_housing', methods=['POST'])
def add_housing():
    """Add a new housing"""
    try:
        housing_name = request.form.get('housing_name')
        housing_location = request.form.get('housing_location', '')
        housing_description = request.form.get('housing_description', '')
        
        if not housing_name:
            flash('اسم السكن مطلوب', 'danger')
            return redirect(url_for('settings'))
        
        new_housing = Housing(
            name=housing_name,
            location=housing_location,
            description=housing_description
        )
        
        db.session.add(new_housing)
        db.session.commit()
        
        flash('تمت إضافة السكن بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding housing: {str(e)}")
        flash(f'حدث خطأ أثناء إضافة السكن: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/edit_housing', methods=['POST'])
def edit_housing():
    """Edit existing housing"""
    try:
        housing_id = request.form.get('housing_id')
        housing_name = request.form.get('housing_name')
        housing_location = request.form.get('housing_location', '')
        housing_description = request.form.get('housing_description', '')
        
        if not housing_id or not housing_name:
            flash('معرف واسم السكن مطلوبان', 'danger')
            return redirect(url_for('settings'))
        
        housing = Housing.query.get(housing_id)
        if not housing:
            flash('لم يتم العثور على السكن', 'danger')
            return redirect(url_for('settings'))
        
        housing.name = housing_name
        housing.location = housing_location
        housing.description = housing_description
        
        db.session.commit()
        
        flash('تم تحديث السكن بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating housing: {str(e)}")
        flash(f'حدث خطأ أثناء تحديث السكن: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/delete_housing', methods=['POST'])
def delete_housing():
    """Delete housing"""
    try:
        housing_id = request.form.get('housing_id')
        
        if not housing_id:
            flash('معرف السكن مطلوب', 'danger')
            return redirect(url_for('settings'))
        
        housing = Housing.query.get(housing_id)
        if not housing:
            flash('لم يتم العثور على السكن', 'danger')
            return redirect(url_for('settings'))
        
        # Check if there are terminals associated with this housing
        if housing.terminals:
            # Update terminals to remove housing association
            for terminal in housing.terminals:
                terminal.housing_id = None
        
        db.session.delete(housing)
        db.session.commit()
        
        flash('تم حذف السكن بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting housing: {str(e)}")
        flash(f'حدث خطأ أثناء حذف السكن: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/add_terminal', methods=['POST'])
def add_terminal():
    """Add a new biometric terminal"""
    try:
        terminal_alias = request.form.get('terminal_alias')
        device_id = request.form.get('device_id')
        terminal_location = request.form.get('terminal_location', '')
        housing_id = request.form.get('housing_id') or None
        
        if not terminal_alias or not device_id:
            flash('اسم ومعرف الجهاز مطلوبان', 'danger')
            return redirect(url_for('settings'))
        
        # Check if terminal with this alias already exists
        existing_terminal = BiometricTerminal.query.filter_by(terminal_alias=terminal_alias).first()
        if existing_terminal:
            flash('يوجد جهاز بصمة بنفس الاسم بالفعل', 'danger')
            return redirect(url_for('settings'))
        
        new_terminal = BiometricTerminal(
            terminal_alias=terminal_alias,
            device_id=device_id,
            location=terminal_location,
            housing_id=housing_id
        )
        
        db.session.add(new_terminal)
        db.session.commit()
        
        flash('تمت إضافة جهاز البصمة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding terminal: {str(e)}")
        flash(f'حدث خطأ أثناء إضافة جهاز البصمة: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/edit_terminal', methods=['POST'])
def edit_terminal():
    """Edit existing biometric terminal"""
    try:
        terminal_id = request.form.get('terminal_id')
        terminal_alias = request.form.get('terminal_alias')
        device_id = request.form.get('device_id')
        terminal_location = request.form.get('terminal_location', '')
        housing_id = request.form.get('housing_id') or None
        
        if not terminal_id or not terminal_alias or not device_id:
            flash('معرف واسم الجهاز مطلوبان', 'danger')
            return redirect(url_for('settings'))
        
        terminal = BiometricTerminal.query.get(terminal_id)
        if not terminal:
            flash('لم يتم العثور على جهاز البصمة', 'danger')
            return redirect(url_for('settings'))
        
        # Check if another terminal with this alias exists
        existing_terminal = BiometricTerminal.query.filter_by(terminal_alias=terminal_alias).first()
        if existing_terminal and str(existing_terminal.id) != str(terminal_id):
            flash('يوجد جهاز بصمة آخر بنفس الاسم', 'danger')
            return redirect(url_for('settings'))
        
        terminal.terminal_alias = terminal_alias
        terminal.device_id = device_id
        terminal.location = terminal_location
        terminal.housing_id = housing_id
        
        db.session.commit()
        
        flash('تم تحديث جهاز البصمة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating terminal: {str(e)}")
        flash(f'حدث خطأ أثناء تحديث جهاز البصمة: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/delete_terminal', methods=['POST'])
def delete_terminal():
    """Delete biometric terminal"""
    try:
        terminal_id = request.form.get('terminal_id')
        
        if not terminal_id:
            flash('معرف الجهاز مطلوب', 'danger')
            return redirect(url_for('settings'))
        
        terminal = BiometricTerminal.query.get(terminal_id)
        if not terminal:
            flash('لم يتم العثور على جهاز البصمة', 'danger')
            return redirect(url_for('settings'))
        
        db.session.delete(terminal)
        db.session.commit()
        
        flash('تم حذف جهاز البصمة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting terminal: {str(e)}")
        flash(f'حدث خطأ أثناء حذف جهاز البصمة: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/remove_terminal_housing', methods=['POST'])
def remove_terminal_housing():
    """Remove housing association from terminal"""
    try:
        terminal_id = request.form.get('terminal_id')
        
        if not terminal_id:
            flash('معرف الجهاز مطلوب', 'danger')
            return redirect(url_for('settings'))
        
        terminal = BiometricTerminal.query.get(terminal_id)
        if not terminal:
            flash('لم يتم العثور على جهاز البصمة', 'danger')
            return redirect(url_for('settings'))
        
        terminal.housing_id = None
        db.session.commit()
        
        flash('تم إزالة ارتباط السكن بجهاز البصمة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing terminal housing: {str(e)}")
        flash(f'حدث خطأ أثناء إزالة ارتباط السكن بجهاز البصمة: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/get_housing_terminals')
def get_housing_terminals():
    """Get terminals for a specific housing (AJAX)"""
    try:
        housing_id = request.args.get('housing_id')
        
        if not housing_id:
            return jsonify({
                'success': False,
                'error': 'معرف السكن مطلوب'
            }), 400
        
        terminals = BiometricTerminal.query.filter_by(housing_id=housing_id).all()
        terminal_list = []
        
        for terminal in terminals:
            terminal_list.append({
                'id': terminal.id,
                'terminal_alias': terminal.terminal_alias,
                'device_id': terminal.device_id,
                'location': terminal.location,
                'housing_id': terminal.housing_id
            })
        
        return jsonify({
            'success': True,
            'terminals': terminal_list
        })
    except Exception as e:
        logger.error(f"Error fetching housing terminals: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        
        # الحصول على إعدادات واجهة المستخدم الموجودة أو إنشاء إعدادات جديدة
        ui_settings = session.get('ui_settings', {})
        
        # تحديث إعدادات مظهر واجهة المستخدم
        if 'weekend_days[]' in request.form:
            weekend_days = request.form.getlist('weekend_days[]')
            ui_settings['weekend_days'] = weekend_days
            logger.info(f"Updated weekend days to: {weekend_days}")
        else:
            # Default to Friday and Saturday
            ui_settings['weekend_days'] = ['4', '5']  # 4=Friday, 5=Saturday
            
        # إعدادات واجهة المستخدم الأخرى 
        ui_fields = [
            'default_view', 'present_color', 'absent_color', 
            'vacation_color', 'transfer_color', 'sick_color', 'eid_color'
        ]
        
        for field in ui_fields:
            if field in request.form:
                ui_settings[field] = request.form.get(field)
        
        # خانات الاختيار الإضافية
        for setting in ['include_logo', 'include_legend', 'landscape_orientation']:
            ui_settings[setting] = 'on' if setting in request.form else 'off'
        
        # حفظ إعدادات واجهة المستخدم في الجلسة
        session['ui_settings'] = ui_settings
            
        flash('Settings saved successfully!', 'success')
        logger.info(f"UI settings saved: {ui_settings}")
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        flash(f'Error saving settings: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/ai_dashboard')
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

@app.route('/ai_anomalies')
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

@app.route('/ai_predictions')
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

@app.route('/ai_patterns')
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

@app.route('/ai_clustering')
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

@app.route('/ai_recommendations')
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

@app.route('/cancel_sync', methods=['GET', 'POST'])
def cancel_sync():
    """Cancel any ongoing data synchronization process"""
    try:
        # Add logic here to cancel any ongoing sync process
        # This might involve setting a flag or stopping a background process
        if hasattr(sync_service, 'cancel_sync'):
            sync_service.cancel_sync()
            flash('Sync operation has been cancelled', 'info')
        else:
            logger.warning("Cancel sync functionality not fully implemented")
            flash('Cancel sync functionality not fully implemented', 'warning')
    except Exception as e:
        logger.error(f"Error cancelling sync: {str(e)}")
        flash(f"Error cancelling sync: {str(e)}", 'danger')
    
    # Redirect back to the previous page or settings
    next_page = request.args.get('next') or request.referrer or url_for('settings')
    return redirect(next_page)

@app.route('/check_sync_status')
def check_sync_status():
    """AJAX endpoint to check current sync status"""
    try:
        # Get the current sync status
        if hasattr(sync_service, 'get_sync_status'):
            status = sync_service.get_sync_status()
        else:
            status = {"status": "unknown", "message": "Sync status function not available"}
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error getting sync status: {str(e)}"
        }), 500

@app.route('/sync_results')
def sync_results():
    """Display detailed sync results and history"""
    try:
        # Get sync logs for history
        sync_logs = SyncLog.query.order_by(SyncLog.sync_time.desc()).limit(20).all()
        
        # Get current sync status
        if hasattr(sync_service, 'get_sync_status'):
            current_status = sync_service.get_sync_status()
        else:
            current_status = {"status": "unknown", "message": "Sync status function not available"}
        
        # Create sync_data dictionary for the template
        last_sync = SyncLog.query.order_by(SyncLog.sync_time.desc()).first()
        
        # Query attendance records for pagination
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Number of records per page
        
        # Build filter query
        query = db.session.query(
            AttendanceRecord.id,
            AttendanceRecord.date,
            AttendanceRecord.clock_in,
            AttendanceRecord.clock_out,
            AttendanceRecord.attendance_status,
            AttendanceRecord.terminal_id_in,
            AttendanceRecord.terminal_id_out,
            AttendanceRecord.work_hours.label('total_time'),
            Employee.name.label('employee_name'),
            Department.name.label('department_name'),
            func.extract('dow', AttendanceRecord.date).label('weekday'),
            BiometricTerminal.terminal_alias.label('terminal_alias_in')
        ).select_from(AttendanceRecord).join(
            Employee, AttendanceRecord.employee_id == Employee.id
        ).join(
            Department, Employee.department_id == Department.id
        ).outerjoin(
            BiometricTerminal, AttendanceRecord.terminal_id_in == BiometricTerminal.id
        )
        
        # Apply filters if provided
        dept_id = request.args.get('department')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_search = request.args.get('employee')
        
        filter_data = {
            'department': dept_id,
            'start_date': start_date,
            'end_date': end_date,
            'employee': employee_search
        }
        
        if dept_id:
            query = query.filter(Employee.department_id == dept_id)
        
        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
        
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
            
        if employee_search:
            query = query.filter(Employee.name.like(f'%{employee_search}%'))
        
        # Count total records for statistics
        records_count = query.count()
        
        # Paginate the results
        pagination = query.order_by(AttendanceRecord.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        attendance_records = pagination.items
        
        # Get min and max dates for display
        min_date = db.session.query(func.min(AttendanceRecord.date)).scalar()
        max_date = db.session.query(func.max(AttendanceRecord.date)).scalar()
        
        # Create sync_data dictionary
        sync_data = {
            'records_count': records_count,
            'start_date': min_date.strftime('%Y-%m-%d') if min_date else 'N/A',
            'end_date': max_date.strftime('%Y-%m-%d') if max_date else 'N/A',
            'last_sync': last_sync.sync_time.strftime('%Y-%m-%d %H:%M:%S') if last_sync else 'N/A'
        }
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        
        return render_template('sync_results.html',
                              sync_logs=sync_logs,
                              current_status=current_status,
                              sync_data=sync_data,
                              attendance_records=attendance_records,
                              pagination=pagination,
                              departments=departments,
                              selected_dept=dept_id,
                              filter_data=filter_data)
    except Exception as e:
        logger.error(f"Error displaying sync results: {str(e)}")
        flash(f"Error displaying sync results: {str(e)}", "danger")
        return redirect(url_for('settings'))

@app.route('/upload_sync', methods=['POST'])
def upload_sync():
    """Handle file upload for manual sync from file"""
    import os
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('settings'))
            
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('settings'))
            
        if file:
            # Save the file
            upload_path = 'attendance_data_upload.txt'
            file.save(upload_path)
            
            # Process the file (you can call your sync code here)
            flash('File uploaded successfully. Processing data...', 'info')
            
            # Start processing in background
            if hasattr(sync_service, 'process_uploaded_file'):
                thread = threading.Thread(
                    target=sync_service.process_uploaded_file,
                    kwargs={'app': app, 'filepath': upload_path}
                )
                thread.daemon = True
                thread.start()
            else:
                flash('File upload feature not fully implemented', 'warning')
            
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        flash(f'Error processing uploaded file: {str(e)}', 'danger')
        
    return redirect(url_for('settings'))

@app.route('/employee_performance')
def employee_performance():
    """View employee performance metrics and analytics"""
    try:
        # Get query parameters
        emp_id = request.args.get('employee_id')
        dept_id = request.args.get('department_id')
        period = request.args.get('period', 'month')  # Default to monthly view
        
        # Get departments for filter dropdown
        departments = Department.query.all()
        
        # Default to all employees if no filters
        employees = []
        selected_employee = None
        
        if dept_id:
            # Filter employees by department
            employees = Employee.query.filter_by(department_id=dept_id).all()
        
        if emp_id:
            # Get specific employee details
            selected_employee = Employee.query.get(emp_id)
            
            if not selected_employee:
                flash("Employee not found", "warning")
                return redirect(url_for('departments'))
        
        # Get performance metrics
        performance_data = {}
        attendance_history = []
        
        if selected_employee:
            # Get attendance records for the employee
            if period == 'month':
                # Last 30 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
            elif period == 'quarter':
                # Last 90 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=90)
            elif period == 'year':
                # Last 365 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=365)
            else:
                # Default to last 30 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
            
            # Query attendance records
            attendance_history = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id == selected_employee.id,
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date
            ).order_by(AttendanceRecord.date).all()
            
            # Calculate performance metrics
            total_days = (end_date - start_date).days + 1
            present_days = sum(1 for record in attendance_history if record.attendance_status == 'P')
            absent_days = sum(1 for record in attendance_history if record.attendance_status == 'A')
            vacation_days = sum(1 for record in attendance_history if record.attendance_status == 'V')
            sick_days = sum(1 for record in attendance_history if record.attendance_status == 'S')
            
            # Calculate other metrics
            attendance_rate = round((present_days / total_days) * 100, 1) if total_days > 0 else 0
            total_hours = sum(record.work_hours or 0 for record in attendance_history)
            overtime_hours = sum(record.overtime_hours or 0 for record in attendance_history)
            
            # Assemble performance data
            performance_data = {
                'employee': selected_employee,
                'attendance_rate': attendance_rate,
                'present_days': present_days,
                'absent_days': absent_days,
                'vacation_days': vacation_days,
                'sick_days': sick_days,
                'total_days': total_days,
                'total_hours': round(total_hours, 1),
                'overtime_hours': round(overtime_hours, 1),
                'period': period,
                'start_date': start_date,
                'end_date': end_date
            }
            
        return render_template('employee_performance.html',
                              departments=departments,
                              employees=employees,
                              selected_dept=dept_id,
                              performance_data=performance_data,
                              attendance_history=attendance_history,
                              period=period)
                              
    except Exception as e:
        logger.error(f"Error in employee performance page: {str(e)}")
        flash(f"Error loading employee performance data: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/api/departments/<int:department_id>/employees')
def get_department_employees(department_id):
    """API endpoint to get employees of a specific department"""
    try:
        department = Department.query.get(department_id)
        if not department:
            return jsonify({'success': False, 'error': 'Department not found'}), 404
        
        employees = Employee.query.filter_by(department_id=department_id).all()
        employees_list = []
        
        for employee in employees:
            housing_name = None
            if employee.housing:
                housing_name = employee.housing.name
                
            employees_list.append({
                'id': employee.id,
                'emp_code': employee.emp_code,
                'name': employee.name,
                'name_ar': employee.name_ar,
                'profession': employee.profession,
                'housing_id': employee.housing_id,
                'housing_name': housing_name,
                'active': employee.active,
                'daily_hours': employee.daily_hours
            })
        
        return jsonify({'success': True, 'employees': employees_list})
    except Exception as e:
        logger.error(f"Error fetching department employees: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/departments/<int:department_id>/statistics')
def get_department_statistics(department_id):
    """API endpoint to get statistics for a specific department"""
    try:
        department = Department.query.get(department_id)
        if not department:
            return jsonify({'success': False, 'error': 'Department not found'}), 404
        
        # Get end date and start date (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get employee IDs for this department
        employee_ids = [e.id for e in Employee.query.filter_by(department_id=department_id).all()]
        
        if not employee_ids:
            return jsonify({
                'success': True, 
                'attendance_stats': {'present': 0, 'absent': 0, 'vacation': 0, 'sick': 0},
                'message': 'No employees found in this department'
            })
        
        # Query attendance records for these employees
        records = AttendanceRecord.query.filter(
            AttendanceRecord.employee_id.in_(employee_ids),
            AttendanceRecord.date >= start_date,
            AttendanceRecord.date <= end_date
        ).all()
        
        # Count by attendance status
        present_count = sum(1 for r in records if r.attendance_status == 'P')
        absent_count = sum(1 for r in records if r.attendance_status == 'A')
        vacation_count = sum(1 for r in records if r.attendance_status == 'V')
        sick_count = sum(1 for r in records if r.attendance_status == 'S')
        
        # Create statistics
        attendance_stats = {
            'present': present_count,
            'absent': absent_count,
            'vacation': vacation_count,
            'sick': sick_count
        }
        
        return jsonify({
            'success': True, 
            'attendance_stats': attendance_stats,
            'employee_count': len(employee_ids),
            'record_count': len(records),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        })
    except Exception as e:
        logger.error(f"Error calculating department statistics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_housing_assignments', methods=['GET', 'POST'])
def update_housing_assignments():
    """Update employee housing assignments based on biometric terminal usage"""
    try:
        # First check how many employees still need housing assignments
        from models import Employee
        employees_without_housing = Employee.query.filter(
            Employee.active == True,
            (Employee.housing_id == None) | (Employee.housing_id == 0)
        ).count()
        
        # Now run the improved algorithm
        updated_count = data_processor.update_employee_housing_from_terminals()
        
        # Check how many still need housing after the update
        remaining_without_housing = Employee.query.filter(
            Employee.active == True,
            (Employee.housing_id == None) | (Employee.housing_id == 0)
        ).count()
        
        if updated_count > 0:
            flash(f'تم تحديث {updated_count} موظف وربطهم بالسكن المناسب بناءً على أجهزة البصمة المستخدمة', 'success')
            flash(f'لا يزال هناك {remaining_without_housing} موظف بدون سكن محدد من أصل {employees_without_housing}', 'info')
        else:
            flash('لم يتم العثور على موظفين يحتاجون إلى تحديث السكن أو لا توجد بيانات استخدام كافية', 'info')
            if employees_without_housing > 0:
                flash(f'هناك {employees_without_housing} موظف نشط بدون سكن محدد. تأكد من أن جميع أجهزة البصمة مرتبطة بسكنات', 'warning')
            
    except Exception as e:
        logger.error(f"خطأ أثناء تحديث السكن للموظفين: {str(e)}")
        flash(f'حدث خطأ أثناء تحديث السكن للموظفين: {str(e)}', 'danger')
    
    # Redirect back to the previous page or settings
    next_page = request.args.get('next') or request.referrer or url_for('settings')
    return redirect(next_page)

# Initialize scheduler when app is ready
with app.app_context():
    scheduler.add_job(
        sync_service.simple_sync_data,
        'interval', 
        hours=4, 
        id='biotime_sync',
        kwargs={'app': app}
    )
    scheduler.start()
    logger.info("Scheduler started - BioTime sync job scheduled every 4 hours")

# Shutdown scheduler when app exits
import atexit
atexit.register(lambda: scheduler.shutdown())

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)