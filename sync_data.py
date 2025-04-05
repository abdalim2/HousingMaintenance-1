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
