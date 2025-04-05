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
    sync_log = None
    # Define required columns
    required_columns = ['emp_code', 'first_name', 'dept_name', 'att_date', 'punch_time']
    
    try:
        # Read data from file - try different formats
        try:
            # First try tab-separated format
            data = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.warning(f"File is missing required columns: {missing_columns}")
                # Try with different column names that might be in the file
                column_mapping = {}
                if 'emp_code' not in data.columns and 'employee_code' in data.columns:
                    column_mapping['employee_code'] = 'emp_code'
                if 'first_name' not in data.columns and 'name' in data.columns:
                    column_mapping['name'] = 'first_name'
                if 'dept_name' not in data.columns and 'department' in data.columns:
                    column_mapping['department'] = 'dept_name'
                if 'att_date' not in data.columns and 'date' in data.columns:
                    column_mapping['date'] = 'att_date'
                
                # Rename columns if mappings exist
                if column_mapping:
                    data.rename(columns=column_mapping, inplace=True)
                
                # Check again for required columns
                missing_columns = [col for col in required_columns if col not in data.columns]
                if missing_columns:
                    # Still missing columns, try comma-separated format
                    data = pd.read_csv(file_path, encoding='utf-8')
                    
                    # Check required columns again
                    missing_columns = [col for col in required_columns if col not in data.columns]
                    if missing_columns:
                        # If still missing, log error and return
                        logger.error(f"Uploaded file is missing required columns: {missing_columns}")
                        raise ValueError(f"Uploaded file is missing required columns: {missing_columns}")
        except Exception as e:
            # Try reading as plain text and parse manually
            logger.warning(f"Could not parse file with pandas: {str(e)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Check if there are any lines
            if not lines:
                logger.error("Uploaded file is empty")
                raise ValueError("Uploaded file is empty")
            
            # Try to identify the delimiter (tab or comma)
            first_line = lines[0].strip()
            delimiter = '\t' if '\t' in first_line else ',' if ',' in first_line else None
            
            if not delimiter:
                logger.error("Could not identify delimiter in file")
                raise ValueError("Could not identify delimiter in file (should be tab or comma separated)")
            
            # Parse header and data
            header = [h.strip() for h in lines[0].split(delimiter)]
            rows = []
            for line in lines[1:]:
                if line.strip():  # Skip empty lines
                    values = [v.strip() for v in line.split(delimiter)]
                    if len(values) >= len(header):
                        row = {header[i]: values[i] for i in range(len(header))}
                        rows.append(row)
            
            # Convert to DataFrame
            data = pd.DataFrame(rows)
            
            # Check if we got any data
            if data.empty:
                logger.error("Could not parse any data from file")
                raise ValueError("Could not parse any data from file")
                
            # Be more flexible with required columns for manually uploaded files
            # As long as we have employee code and date, we can work with it
            minimal_required = ['emp_code', 'att_date']
            
            # Try to map common column names
            column_mapping = {}
            for col in data.columns:
                col_lower = col.lower()
                if 'emp' in col_lower and 'code' in col_lower and 'emp_code' not in data.columns:
                    column_mapping[col] = 'emp_code'
                elif 'employee' in col_lower and 'code' in col_lower and 'emp_code' not in data.columns:
                    column_mapping[col] = 'emp_code'
                elif 'date' in col_lower and 'att_date' not in data.columns:
                    column_mapping[col] = 'att_date'
                elif 'time' in col_lower and 'punch_time' not in data.columns:
                    column_mapping[col] = 'punch_time'
                elif 'name' in col_lower and 'first_name' not in data.columns:
                    column_mapping[col] = 'first_name'
                elif 'dept' in col_lower and 'dept_name' not in data.columns:
                    column_mapping[col] = 'dept_name'
            
            # Apply mappings
            if column_mapping:
                data.rename(columns=column_mapping, inplace=True)
            
            # Check minimal required columns
            missing_minimal = [col for col in minimal_required if col not in data.columns]
            if missing_minimal:
                logger.error(f"Uploaded file is missing essential columns: {missing_minimal}")
                raise ValueError(f"Uploaded file is missing essential columns: {missing_minimal}")
                
            # If we got here, we have the minimal required data to proceed
        
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
        
        # First, try to process data specifically for each department
        for dept_id in DEPARTMENTS:
            try:
                # Filter data for this department if possible
                dept_data = data
                if 'dept_id' in data.columns:
                    dept_data = data[data['dept_id'] == str(dept_id)]
                elif 'dept_name' in data.columns:
                    # Get department name for this ID
                    dept = Department.query.filter_by(dept_id=str(dept_id)).first()
                    if dept:
                        dept_data = data[data['dept_name'].str.contains(dept.name, case=False, na=False)]
                
                if not dept_data.empty:
                    records = process_manual_upload_data(dept_id, dept_data)
                    if records > 0:
                        department_records[dept_id] = records
                        total_records += records
            except Exception as e:
                error_msg = f"Error processing department {dept_id} from uploaded file: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # If no records were processed by department, try processing all data at once
        if total_records == 0:
            try:
                records = process_manual_upload_data(None, data)
                total_records = records
                department_records["all"] = records
            except Exception as e:
                error_msg = f"Error processing all data from uploaded file: {str(e)}"
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
        if sync_log:
            sync_log.status = "error"
            sync_log.error_message = str(e)
            db.session.commit()
        return 0

def process_manual_upload_data(dept_id, data):
    """
    Process manual upload data for a specific department
    
    Args:
        dept_id: ID of the department
        data: DataFrame containing attendance data
        
    Returns:
        Number of records processed
    """
    # Import here to avoid circular imports
    from app import db
    from models import Department, Employee, AttendanceRecord
    
    records_processed = 0
    
    # Process each row in the dataframe
    for _, row in data.iterrows():
        try:
            # Get employee code
            emp_code = None
            if 'emp_code' in row:
                emp_code = str(row['emp_code'])
            elif 'employee_code' in row:
                emp_code = str(row['employee_code'])
            
            if not emp_code:
                logger.warning("Skipping row: No employee code found")
                continue
                
            # Get or create employee
            employee = Employee.query.filter_by(emp_code=emp_code).first()
            if not employee:
                # Try to get employee name
                name = None
                if 'first_name' in row and 'last_name' in row:
                    name = f"{row['first_name']} {row['last_name']}"
                elif 'first_name' in row:
                    name = row['first_name']
                elif 'name' in row:
                    name = row['name']
                
                if not name:
                    logger.warning(f"Skipping row: No name found for employee {emp_code}")
                    continue
                    
                # Get department if not specified
                department_id = None
                if dept_id:
                    dept = Department.query.filter_by(dept_id=str(dept_id)).first()
                    if dept:
                        department_id = dept.id
                else:
                    # Try to get department from data
                    dept_name = None
                    if 'dept_name' in row:
                        dept_name = row['dept_name']
                    elif 'department' in row:
                        dept_name = row['department']
                    
                    if dept_name:
                        dept = Department.query.filter(Department.name.ilike(f"%{dept_name}%")).first()
                        if dept:
                            department_id = dept.id
                
                # Create new employee
                employee = Employee(
                    emp_code=emp_code,
                    name=name,
                    department_id=department_id
                )
                db.session.add(employee)
                db.session.flush()  # Get ID without committing
            
            # Get attendance date
            att_date = None
            if 'att_date' in row:
                att_date = row['att_date']
            elif 'date' in row:
                att_date = row['date']
                
            if not att_date:
                logger.warning(f"Skipping row: No date found for employee {emp_code}")
                continue
                
            # Parse date
            try:
                if isinstance(att_date, str):
                    # Try different date formats
                    date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']
                    for date_format in date_formats:
                        try:
                            parsed_date = datetime.strptime(att_date, date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked
                        logger.warning(f"Skipping row: Could not parse date '{att_date}' for employee {emp_code}")
                        continue
                else:
                    # Try to convert to date if it's already a datetime
                    parsed_date = att_date.date() if hasattr(att_date, 'date') else att_date
            except Exception as e:
                logger.warning(f"Skipping row: Error parsing date '{att_date}' for employee {emp_code}: {str(e)}")
                continue
            
            # Check if record already exists
            existing_record = AttendanceRecord.query.filter_by(
                employee_id=employee.id,
                date=parsed_date
            ).first()
            
            if existing_record:
                # Update existing record
                if 'punch_time' in row and row['punch_time']:
                    punch_time = row['punch_time']
                    if isinstance(punch_time, str):
                        try:
                            # Try to parse time
                            time_formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
                            for time_format in time_formats:
                                try:
                                    parsed_time = datetime.strptime(punch_time, time_format).time()
                                    break
                                except ValueError:
                                    continue
                            else:
                                logger.warning(f"Could not parse time '{punch_time}' for employee {emp_code}")
                                continue
                                
                            # Combine date and time
                            dt = datetime.combine(parsed_date, parsed_time)
                            
                            # Check if check-in or check-out
                            punch_state = row.get('punch_state', '').lower()
                            if punch_state == 'in' or 'in' in punch_state:
                                if not existing_record.clock_in or dt < existing_record.clock_in:
                                    existing_record.clock_in = dt
                            elif punch_state == 'out' or 'out' in punch_state:
                                if not existing_record.clock_out or dt > existing_record.clock_out:
                                    existing_record.clock_out = dt
                        except Exception as e:
                            logger.warning(f"Error processing punch time '{punch_time}': {str(e)}")
                
                # Update attendance status if available
                if 'attendance_status' in row and row['attendance_status']:
                    status = row['attendance_status'].upper()
                    if status in ['P', 'A', 'V', 'T', 'S', 'E']:
                        existing_record.attendance_status = status
                
                # Update total time if available (and clock in/out are set)
                if existing_record.clock_in and existing_record.clock_out:
                    time_diff = existing_record.clock_out - existing_record.clock_in
                    total_hours = time_diff.total_seconds() / 3600
                    existing_record.total_time = f"{total_hours:.2f}"
                
                existing_record.updated_at = datetime.utcnow()
                records_processed += 1
            else:
                # Create new record
                record = AttendanceRecord(
                    employee_id=employee.id,
                    date=parsed_date,
                    weekday=parsed_date.strftime('%A')
                )
                
                # Set punch times if available
                if 'punch_time' in row and row['punch_time']:
                    punch_time = row['punch_time']
                    if isinstance(punch_time, str):
                        try:
                            # Try to parse time
                            time_formats = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']
                            for time_format in time_formats:
                                try:
                                    parsed_time = datetime.strptime(punch_time, time_format).time()
                                    break
                                except ValueError:
                                    continue
                            else:
                                logger.warning(f"Could not parse time '{punch_time}' for employee {emp_code}")
                                continue
                                
                            # Combine date and time
                            dt = datetime.combine(parsed_date, parsed_time)
                            
                            # Check if check-in or check-out
                            punch_state = row.get('punch_state', '').lower()
                            if punch_state == 'in' or 'in' in punch_state:
                                record.clock_in = dt
                            elif punch_state == 'out' or 'out' in punch_state:
                                record.clock_out = dt
                        except Exception as e:
                            logger.warning(f"Error processing punch time '{punch_time}': {str(e)}")
                
                # Set attendance status if available
                if 'attendance_status' in row and row['attendance_status']:
                    status = row['attendance_status'].upper()
                    if status in ['P', 'A', 'V', 'T', 'S', 'E']:
                        record.attendance_status = status
                
                # Calculate total time if both clock in and out are set
                if record.clock_in and record.clock_out:
                    time_diff = record.clock_out - record.clock_in
                    total_hours = time_diff.total_seconds() / 3600
                    record.total_time = f"{total_hours:.2f}"
                
                db.session.add(record)
                records_processed += 1
        
        except Exception as e:
            logger.error(f"Error processing row: {str(e)}")
            continue
    
    # Commit all changes
    db.session.commit()
    
    return records_processed

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
