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
BIOTIME_API_BASE_URL = "http://213.210.196.115:8585/att/api/transactionReport/export/"
BIOTIME_USERNAME = os.environ.get("BIOTIME_USERNAME", "raghad")
BIOTIME_PASSWORD = os.environ.get("BIOTIME_PASSWORD", "A1111111")
DEPARTMENTS = [3, 4, 5, 6, 9, 10, 11, 15, 18, 19, 21, 23, 26]

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
    # Format dates with time for the new API
    start_datetime = f"{start_date} 00:00:00"
    end_datetime = f"{end_date} 23:59:59"
    
    # For transaction report API, we need to use all departments in one request
    departments_str = ",".join(str(d) for d in DEPARTMENTS)
    
    params = {
        "export_headers": "emp_code,first_name,dept_name,att_date,punch_time,punch_state,source",
        "start_date": start_datetime,
        "end_date": end_datetime,
        "departments": departments_str,
        "employees": -1,
        "page_size": 999999,
        "export_type": "txt",
        "page": 1,
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
        # Filter data by department_id
        dept_data = data[data['dept_name'].str.contains(f"Department {department_id}", na=False)] if 'dept_name' in data.columns else data
        
        if dept_data.empty:
            logger.warning(f"No data available for department {department_id}")
            return 0
        
        # First ensure department exists
        dept = Department.query.filter_by(dept_id=str(department_id)).first()
        if not dept:
            # Get department name from the data
            dept_name = dept_data['dept_name'].iloc[0] if 'dept_name' in dept_data.columns else f"Department {department_id}"
            dept = Department(dept_id=str(department_id), name=dept_name, active=True)
            db.session.add(dept)
            db.session.commit()
            logger.info(f"Created new department: {dept_name} (ID: {department_id})")
        
        # Group the data by employee and date
        employee_records = {}
        
        # Process each transaction record and group by employee and date
        for _, row in dept_data.iterrows():
            try:
                # Get or create employee
                emp_code = str(row['emp_code'])
                
                # Create record key (employee_code + date)
                att_date = datetime.strptime(row['att_date'], '%Y-%m-%d').date() if 'att_date' in row else None
                if not att_date:
                    continue
                    
                record_key = f"{emp_code}_{att_date.isoformat()}"
                
                # Determine punch type
                punch_state = row.get('punch_state', '').lower() if pd.notna(row.get('punch_state')) else ''
                punch_time = row.get('punch_time') if pd.notna(row.get('punch_time')) else None
                
                if not punch_time:
                    continue
                    
                # Initialize record if it doesn't exist
                if record_key not in employee_records:
                    employee_records[record_key] = {
                        'emp_code': emp_code,
                        'date': att_date,
                        'first_name': row.get('first_name', '') if pd.notna(row.get('first_name')) else '',
                        'dept_name': row.get('dept_name', '') if pd.notna(row.get('dept_name')) else '',
                        'source': row.get('source', '') if pd.notna(row.get('source')) else '',
                        'clock_in': None,
                        'clock_out': None,
                        'weekday': att_date.strftime('%A')  # Get weekday name
                    }
                
                # Parse punch time 
                try:
                    punch_datetime = datetime.strptime(f"{row['att_date']} {punch_time}", '%Y-%m-%d %H:%M:%S')
                    
                    # Determine if this is clock in or clock out
                    if 'in' in punch_state:
                        # Set as clock in if it's earlier than current clock in or if no clock in exists
                        if employee_records[record_key]['clock_in'] is None or punch_datetime < employee_records[record_key]['clock_in']:
                            employee_records[record_key]['clock_in'] = punch_datetime
                    elif 'out' in punch_state:
                        # Set as clock out if it's later than current clock out or if no clock out exists
                        if employee_records[record_key]['clock_out'] is None or punch_datetime > employee_records[record_key]['clock_out']:
                            employee_records[record_key]['clock_out'] = punch_datetime
                except Exception as e:
                    logger.error(f"Error parsing punch time: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing transaction record: {str(e)}")
                continue
        
        # Process the aggregated records
        records_processed = 0
        
        for record_key, record_data in employee_records.items():
            try:
                emp_code = record_data['emp_code']
                att_date = record_data['date']
                
                # Get or create employee
                employee = Employee.query.filter_by(emp_code=emp_code).first()
                if not employee:
                    # Create new employee
                    employee = Employee(
                        emp_code=emp_code,
                        name=record_data.get('first_name', ''),
                        department_id=dept.id if dept else None
                    )
                    db.session.add(employee)
                    db.session.commit()
                
                # Calculate total time if both clock in and clock out exist
                total_time = ''
                if record_data['clock_in'] and record_data['clock_out']:
                    time_diff = record_data['clock_out'] - record_data['clock_in']
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    total_time = f"{hours:02d}:{minutes:02d}"
                
                # Determine attendance status
                status = 'P'  # Default to Present
                if not record_data['clock_in'] and not record_data['clock_out']:
                    status = 'A'  # Absent if no clock in/out
                
                # Check if attendance record already exists for this employee and date
                attendance = AttendanceRecord.query.filter_by(
                    employee_id=employee.id,
                    date=att_date
                ).first()
                
                if attendance:
                    # Update existing record
                    attendance.clock_in = record_data['clock_in']
                    attendance.clock_out = record_data['clock_out']
                    attendance.total_time = total_time
                    attendance.weekday = record_data['weekday']
                    attendance.attendance_status = status
                    attendance.terminal_alias_in = record_data.get('source', '')
                    attendance.updated_at = datetime.utcnow()
                else:
                    # Create new attendance record
                    attendance = AttendanceRecord(
                        employee_id=employee.id,
                        date=att_date,
                        weekday=record_data['weekday'],
                        clock_in=record_data['clock_in'],
                        clock_out=record_data['clock_out'],
                        total_time=total_time,
                        attendance_status=status,
                        terminal_alias_in=record_data.get('source', '')
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

def process_uploaded_file(file_path):
    """
    Process an uploaded file containing attendance data
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        Number of records processed
    """
    # Import here to avoid circular imports
    from app import db
    from models import Department, Employee, AttendanceRecord, SyncLog
    
    total_records = 0
    
    try:
        # Read data from file
        data = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        
        if data.empty:
            logger.warning("Uploaded file contains no data")
            return 0
            
        # Create sync log entry
        sync_log = SyncLog(
            sync_time=datetime.utcnow(),
            status="in_progress",
            departments_synced="Manual upload"
        )
        db.session.add(sync_log)
        db.session.commit()
        
        # Process data for each department
        department_records = {}
        errors = []
        
        for dept_id in DEPARTMENTS:
            try:
                records = process_department_data(dept_id, data)
                if records > 0:
                    department_records[dept_id] = records
                    total_records += records
            except Exception as e:
                error_msg = f"Error processing department {dept_id} from uploaded file: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                
        # Update sync log
        if sync_log:
            sync_log.status = "success" if not errors else "partial"
            sync_log.records_synced = total_records
            
            if department_records:
                departments_str = ", ".join([f"Dept {dept_id}: {count} records" for dept_id, count in department_records.items()])
                sync_log.departments_synced = f"Manual upload - {departments_str}"
            
            sync_log.error_message = "\n".join(errors) if errors else None
            db.session.commit()
        
        logger.info(f"Manual sync completed: {total_records} records processed from uploaded file")
        return total_records
        
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        if 'sync_log' in locals() and sync_log:
            sync_log.status = "error"
            sync_log.error_message = str(e)
            db.session.commit()
        return 0

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
        
        # Fetch all data in one request
        data = fetch_biotime_data(None, start_date_str, end_date_str)
        
        if data is not None and not data.empty:
            # Process data for each department
            for dept_id in DEPARTMENTS:
                try:
                    # Process the data
                    records = process_department_data(dept_id, data)
                    total_records += records
                    if records > 0:
                        synced_depts.append(str(dept_id))
                        logger.info(f"Successfully synced department {dept_id} - {records} records")
                except Exception as e:
                    error_msg = f"Error processing department {dept_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        else:
            error_msg = "No data fetched from BioTime API"
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
