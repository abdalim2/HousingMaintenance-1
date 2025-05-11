"""
Database utilities to help with common tasks and prevent errors
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)

def safe_db_operation(func):
    """
    Decorator for database operations that ensures:
    1. All database objects are converted to dictionaries before returning
    2. Sessions are properly closed in case of errors
    3. Proper error logging

    Usage:
    @safe_db_operation
    def my_db_function():
        # Your code that interacts with the database
        return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from models import db
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            # Try to rollback if this was a transaction
            try:
                db.session.rollback()
            except:
                pass
            raise
    return wrapper

def convert_db_results(records, conversion_func=None):
    """
    Convert database records to dictionaries to prevent DetachedInstanceError
    
    Args:
        records: List or single SQLAlchemy model instance
        conversion_func: Function to convert a single record (if None, uses a generic converter)
        
    Returns:
        List of dictionaries or single dictionary representing the records
    """
    from optimized_timesheet import attendance_record_to_dict, temp_attendance_to_dict
    
    # Default converters for common types
    def get_converter(record):
        from models import AttendanceRecord, TempAttendance
        
        if conversion_func:
            return conversion_func
        elif isinstance(record, AttendanceRecord):
            return attendance_record_to_dict
        elif isinstance(record, TempAttendance):
            return temp_attendance_to_dict
        else:
            # Generic converter
            return lambda r: {c.name: getattr(r, c.name) for c in r.__table__.columns}
    
    # Handle None
    if records is None:
        return None
    
    # Handle lists
    if isinstance(records, list):
        result = []
        for record in records:
            if record is not None:
                converter = get_converter(record)
                result.append(converter(record))
            else:
                result.append(None)
        return result
    
    # Handle single record
    converter = get_converter(records)
    return converter(records)
