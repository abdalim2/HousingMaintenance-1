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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    terminal_in = db.relationship('BiometricTerminal', foreign_keys=[terminal_id_in])
    terminal_out = db.relationship('BiometricTerminal', foreign_keys=[terminal_id_out])
    
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),
    )
    
    def __repr__(self):
        return f'<AttendanceRecord {self.employee_id} on {self.date}>'

class SyncLog(db.Model):
    """Log of data synchronization with BioTime"""
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    start_date = db.Column(db.String(20), nullable=True)  # تاريخ بداية النطاق المزامن
    end_date = db.Column(db.String(20), nullable=True)    # تاريخ نهاية النطاق المزامن
    status = db.Column(db.String(20), nullable=False)  # success, error, in_progress
    step = db.Column(db.String(20), nullable=True)  # connect, download, process, save, complete
    records_synced = db.Column(db.Integer, default=0)
    records_processed = db.Column(db.Integer, default=0)  # عدد السجلات التي تمت معالجتها
    departments_synced = db.Column(db.String(200))
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SyncLog {self.sync_time} - {self.status}>'

class MonthPeriod(db.Model):
    """Model for storing monthly period definitions based on company calendar"""
    __tablename__ = 'month_periods'
    
    id = db.Column(db.Integer, primary_key=True)
    month_code = db.Column(db.String(10), nullable=False)  # Format: MM/YY (e.g., 01/25)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_in_month = db.Column(db.Integer, nullable=False)
    hours_in_month = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<MonthPeriod {self.month_code}: {self.start_date} - {self.end_date}>'

class TempAttendance(db.Model):
    __tablename__ = 'temp_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(50))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    dept_name = db.Column(db.String(100))
    att_date = db.Column(db.Date)
    punch_time = db.Column(db.String(20))
    punch_state = db.Column(db.String(50))
    terminal_alias = db.Column(db.String(100))
    sync_id = db.Column(db.Integer)  # لربط البيانات بعملية مزامنة محددة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TempAttendance {self.emp_code} {self.att_date} {self.punch_time}>"
    
    def save(self):
        """Save the TempAttendance record to the database."""
        db.session.add(self)
        db.session.commit()