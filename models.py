from datetime import datetime
import sys

# Get the SQLAlchemy database instance from app module
from app import db

class Department(db.Model):
    """Department model representing different organizational departments"""
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
    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(20), unique=True, nullable=False)  # Employee code from BioTime
    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100))  # Arabic name
    profession = db.Column(db.String(100))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='employee', lazy=True)
    
    def __repr__(self):
        return f'<Employee {self.emp_code}: {self.name}>'

class AttendanceRecord(db.Model):
    """Attendance record for employee on specific date"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    weekday = db.Column(db.String(10))
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    total_time = db.Column(db.String(20))
    attendance_status = db.Column(db.String(20), default='P')  # P=Present, A=Absent, V=Vacation, T=Transfer, S=Sick, E=Eid, etc.
    terminal_alias_in = db.Column(db.String(100))
    terminal_alias_out = db.Column(db.String(100))
    exception = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),
    )
    
    def __repr__(self):
        return f'<AttendanceRecord {self.employee_id} on {self.date}>'

class SyncLog(db.Model):
    """Log of data synchronization with BioTime"""
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # success, error
    records_synced = db.Column(db.Integer, default=0)
    departments_synced = db.Column(db.String(200))
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SyncLog {self.sync_time} - {self.status}>'
