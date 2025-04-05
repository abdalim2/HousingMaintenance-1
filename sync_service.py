import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import tempfile
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)

# BioTime API configuration
BIOTIME_API_BASE_URL = "http://172.16.16.13:8585/att/api/totalTimeCardReport/export/"
BIOTIME_USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
BIOTIME_PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")
DEPARTMENTS = [11, 6, 3, 18, 15, 19, 23, 10, 9, 5, 4, 26, 21]

def fetch_biotime_data(department_id, start_date, end_date):
    """
    Fetch attendance data from BioTime API for a specific department
    
    Args:
        department_id: ID of the department to fetch data for
        start_date: Start date for data fetch (format: YYYY-MM-DD)
        end_date: End date for data fetch (format: YYYY-MM-DD)
        
    Returns:
        DataFrame containing attendance data
    """
    params = {
        "export_headers": "emp_code,dept_name,att_date,weekday,att_exception,terminal_alias_in,clock_in,clock_out,total_time",
        "start_date": start_date,
        "end_date": end_date,
        "departments": department_id,
        "employees": -1,
        "page_size": 999999,
        "export_type": "txt",
        "page": 1,
        "export_style": "",
        "limit": 999999
    }
    
    try:
        logger.debug(f"Fetching data for department {department_id} from {start_date} to {end_date}")
        
        # Make API request
        response = requests.get(
            BIOTIME_API_BASE_URL,
            params=params,
            auth=(BIOTIME_USERNAME, BIOTIME_PASSWORD),
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            return None
        
        # Save response to temporary file to handle potential encoding issues
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='wb') as temp:
            temp.write(response.content)
            temp_filename = temp.name
        
        # Read data from file
        data = pd.read_csv(temp_filename, sep='\t', encoding='utf-8')
        
        # Clean up temp file
        os.unlink(temp_filename)
        
        logger.debug(f"Successfully fetched {len(data)} records for department {department_id}")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return None

def process_department_data(department_id, data):
    """
    Process department data from BioTime and update database
    
    Args:
        department_id: ID of the department
        data: DataFrame containing attendance data
    """
    # Import here to avoid circular imports
    from app import db
    from models import Department, Employee, AttendanceRecord
    
    try:
        # First ensure department exists
        dept = Department.query.filter_by(dept_id=str(department_id)).first()
        if not dept and not data.empty:
            # Get department name from the first row
            dept_name = data['dept_name'].iloc[0] if 'dept_name' in data.columns else f"Department {department_id}"
            dept = Department(dept_id=str(department_id), name=dept_name, active=True)
            db.session.add(dept)
            db.session.commit()
            logger.info(f"Created new department: {dept_name} (ID: {department_id})")
        
        # Process each record
        records_processed = 0
        
        for _, row in data.iterrows():
            # Get or create employee
            emp_code = str(row['emp_code'])
            employee = Employee.query.filter_by(emp_code=emp_code).first()
            
            if not employee:
                # Create new employee
                employee = Employee(
                    emp_code=emp_code,
                    name=row.get('name', ''),  # This might be missing in the data
                    department_id=dept.id if dept else None
                )
                db.session.add(employee)
                db.session.commit()
            
            # Parse date and attendance data
            try:
                att_date = datetime.strptime(row['att_date'], '%Y-%m-%d').date()
                
                # Determine attendance status based on exception
                status = 'P'  # Default to Present
                if pd.notna(row.get('att_exception')):
                    exception = row['att_exception'].lower()
                    if 'absent' in exception:
                        status = 'A'  # Absence
                    elif 'vacation' in exception:
                        status = 'V'  # Vacation
                    elif 'transfer' in exception:
                        status = 'T'  # Transfer
                    elif 'sick' in exception:
                        status = 'S'  # Sick
                    elif 'eid' in exception:
                        status = 'E'  # Eid
                
                # Parse clock in/out times
                clock_in = None
                if pd.notna(row.get('clock_in')):
                    try:
                        clock_in = datetime.strptime(f"{row['att_date']} {row['clock_in']}", '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                clock_out = None
                if pd.notna(row.get('clock_out')):
                    try:
                        clock_out = datetime.strptime(f"{row['att_date']} {row['clock_out']}", '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                # Check if attendance record already exists for this employee and date
                attendance = AttendanceRecord.query.filter_by(
                    employee_id=employee.id,
                    date=att_date
                ).first()
                
                if attendance:
                    # Update existing record
                    attendance.clock_in = clock_in
                    attendance.clock_out = clock_out
                    attendance.total_time = row.get('total_time', '')
                    attendance.weekday = row.get('weekday', '')
                    attendance.attendance_status = status
                    attendance.exception = row.get('att_exception', '')
                    attendance.terminal_alias_in = row.get('terminal_alias_in', '')
                    attendance.updated_at = datetime.utcnow()
                else:
                    # Create new attendance record
                    attendance = AttendanceRecord(
                        employee_id=employee.id,
                        date=att_date,
                        weekday=row.get('weekday', ''),
                        clock_in=clock_in,
                        clock_out=clock_out,
                        total_time=row.get('total_time', ''),
                        attendance_status=status,
                        terminal_alias_in=row.get('terminal_alias_in', ''),
                        exception=row.get('att_exception', '')
                    )
                    db.session.add(attendance)
                
                records_processed += 1
                
                # Commit in batches to avoid performance issues
                if records_processed % 100 == 0:
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Error processing attendance record: {str(e)}")
                continue
        
        # Final commit for any remaining records
        db.session.commit()
        logger.info(f"Processed {records_processed} records for department {department_id}")
        
        return records_processed
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing department data: {str(e)}")
        raise

def sync_data(app=None):
    """
    Sync attendance data from BioTime
    
    Args:
        app: Flask application instance (for creating application context)
    """
    # Import here to avoid circular imports
    from app import db
    from models import Department, Employee, AttendanceRecord, SyncLog
    
    # Get app context if provided
    ctx = None
    if app:
        ctx = app.app_context()
        ctx.push()
    
    total_records = 0
    errors = []
    synced_depts = []
    sync_log = None
    
    # Calculate date range (past month to current date)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Format dates for API
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Starting BioTime data sync from {start_date_str} to {end_date_str}")
    
    try:
        # Create sync log entry
        sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="in_progress",
            departments_synced=",".join(str(d) for d in DEPARTMENTS)
        )
        db.session.add(sync_log)
        db.session.commit()
        
        # Process each department
        for dept_id in DEPARTMENTS:
            try:
                # Fetch data from BioTime
                data = fetch_biotime_data(dept_id, start_date_str, end_date_str)
                
                if data is not None and not data.empty:
                    # Process the data
                    records = process_department_data(dept_id, data)
                    total_records += records
                    synced_depts.append(str(dept_id))
                    logger.info(f"Successfully synced department {dept_id} - {records} records")
                else:
                    logger.warning(f"No data available for department {dept_id}")
            
            except Exception as e:
                error_msg = f"Error syncing department {dept_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Update sync log
        if sync_log:
            sync_log.status = "success" if not errors else "partial"
            sync_log.records_synced = total_records
            sync_log.departments_synced = ",".join(synced_depts)
            sync_log.error_message = "\n".join(errors) if errors else None
            db.session.commit()
        
        logger.info(f"Data sync completed: {total_records} records synced")
    
    except Exception as e:
        logger.error(f"Sync process failed: {str(e)}")
        if sync_log:
            sync_log.status = "error"
            sync_log.error_message = str(e)
            db.session.commit()
    
    finally:
        # Clean up app context if it was pushed
        if ctx:
            ctx.pop()
