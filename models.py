from datetime import datetime
import sys

# Import the database connection from database.py
from database import db

class Housing(db.Model):
    """Housing model representing different housing locations"""
    __tablename__ = 'housings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    # Relationships
    terminals = db.relationship('BiometricTerminal', backref='housing', lazy=True)

    def __repr__(self):
        return f'<Housing {self.name}>'

class BiometricTerminal(db.Model):
    """Biometric Terminal model representing different fingerprint devices"""
    __tablename__ = 'biometric_terminals'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    terminal_alias = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    housing_id = db.Column(db.Integer, db.ForeignKey('housings.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<BiometricTerminal {self.terminal_alias}>'

class Department(db.Model):
    """Department model representing different organizational departments"""
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    dept_id = db.Column(db.String(20), unique=True, nullable=False)  # ID from BioTime
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)

    # Relationships
    employees = db.relationship('Employee', backref='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.name}>'

class Employee(db.Model):
    """Employee model storing employee information"""
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(20), unique=True, nullable=False)  # Employee code from BioTime
    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100))  # Arabic name
    profession = db.Column(db.String(100))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # Updated to match Department __tablename__
    housing_id = db.Column(db.Integer, db.ForeignKey('housings.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    daily_hours = db.Column(db.Float, default=8.0)  # Default daily work hours set to 8.0

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='employee', lazy=True)
    housing = db.relationship('Housing', backref='employees', lazy=True)

    def __repr__(self):
        return f'<Employee {self.emp_code}: {self.name}>'

class AttendanceRecord(db.Model):
    """Attendance record for employee on specific date"""
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    weekday = db.Column(db.String(10))
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    total_time = db.Column(db.String(20))
    work_hours = db.Column(db.Float, default=0.0)  # عدد ساعات العمل الفعلية
    overtime_hours = db.Column(db.Float, default=0.0)  # عدد ساعات العمل الإضافي
    attendance_status = db.Column(db.String(20), default='P')  # P=Present, A=Absent, V=Vacation, T=Transfer, S=Sick, E=Eid, etc.
    terminal_id_in = db.Column(db.Integer, db.ForeignKey('biometric_terminals.id'), nullable=True)
    terminal_id_out = db.Column(db.Integer, db.ForeignKey('biometric_terminals.id'), nullable=True)
    terminal_alias_in = db.Column(db.String(100))
    terminal_alias_out = db.Column(db.String(100))
    exception = db.Column(db.String(100))
    notes = db.Column(db.Text, nullable=True)  # Added notes column for sync comments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_synced = db.Column(db.Boolean, default=False)
    sync_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<AttendanceRecord {self.employee.name} on {self.date}>'

class SyncLog(db.Model):
    """Synchronization log tracking each sync operation"""
    __tablename__ = 'sync_logs'

    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, failed, cancelled
    step = db.Column(db.String(50))  # init, fetch, extract, process, complete
    progress = db.Column(db.Integer, default=0)  # 0-100%
    message = db.Column(db.String(255))
    error = db.Column(db.Text)
    departments_synced = db.Column(db.String(255))  # Comma-separated list of department IDs
    records_synced = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SyncLog {self.id} on {self.sync_time}: {self.status}>'

class MonthPeriod(db.Model):
    """Month period for attendance reporting"""
    __tablename__ = 'month_periods'

    id = db.Column(db.Integer, primary_key=True)
    month_code = db.Column(db.String(10), unique=True)  # Format: MM/YY
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_in_month = db.Column(db.Integer, default=30)
    hours_in_month = db.Column(db.Float, default=240.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MonthPeriod {self.month_code}: {self.start_date} to {self.end_date}>'

class TempAttendance(db.Model):
    """Temporary table for storing attendance data during synchronization"""
    __tablename__ = 'temp_attendance'

    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(20))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    dept_name = db.Column(db.String(100))
    att_date = db.Column(db.Date)
    punch_time = db.Column(db.String(20))
    punch_state = db.Column(db.String(10))  # Check-in or Check-out
    terminal_alias = db.Column(db.String(100))
    sync_id = db.Column(db.Integer, nullable=True)  # Reference to the sync operation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TempAttendance {self.emp_code} on {self.att_date}: {self.punch_state}>'

class EmployeeVacation(db.Model):
    """Employee Vacation model to track vacation periods"""
    __tablename__ = 'employee_vacations'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with Employee
    employee = db.relationship('Employee', backref='vacations', lazy=True)

    def __repr__(self):
        return f'<EmployeeVacation {self.employee.name if self.employee else "Unknown"} from {self.start_date} to {self.end_date}>'

class EmployeeTransfer(db.Model):
    """Employee Transfer model to track transfers between sites/departments"""
    __tablename__ = 'employee_transfers'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    from_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    to_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    from_housing_id = db.Column(db.Integer, db.ForeignKey('housings.id'), nullable=True)
    to_housing_id = db.Column(db.Integer, db.ForeignKey('housings.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', backref='transfers', lazy=True)
    from_department = db.relationship('Department', foreign_keys=[from_department_id])
    to_department = db.relationship('Department', foreign_keys=[to_department_id])
    from_housing = db.relationship('Housing', foreign_keys=[from_housing_id])
    to_housing = db.relationship('Housing', foreign_keys=[to_housing_id])

    def __repr__(self):
        return f'<EmployeeTransfer {self.employee.name if self.employee else "Unknown"} from {self.start_date} to {self.end_date}>'

class EmployeeException(db.Model):
    """Employee Exception model to track special exceptions with 8-hour compensation"""
    __tablename__ = 'employee_exceptions'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    hours_credited = db.Column(db.Float, default=8.0)  # Default to 8 hours compensation
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with Employee
    employee = db.relationship('Employee', backref='exceptions', lazy=True)

    def __repr__(self):
        return f'<EmployeeException {self.employee.name if self.employee else "Unknown"} on {self.date}>'

class EmployeeSickLeave(db.Model):
    """Employee Sick Leave model to track medical absences"""
    __tablename__ = 'employee_sick_leaves'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    medical_certificate = db.Column(db.Boolean, default=False)  # Whether medical certificate was provided
    reason = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with Employee
    employee = db.relationship('Employee', backref='sick_leaves', lazy=True)

    def __repr__(self):
        return f'<EmployeeSickLeave {self.employee.name if self.employee else "Unknown"} from {self.start_date} to {self.end_date}>'

class AppearanceSettings(db.Model):
    """User interface appearance settings"""
    __tablename__ = 'appearance_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, default=1)  # Default to user 1 if not logged in
    settings = db.Column(db.Text, nullable=False)  # JSON string of settings
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AppearanceSettings for user {self.user_id}>'

class SystemSettings(db.Model):
    """System-wide settings"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSettings {self.key}>'
