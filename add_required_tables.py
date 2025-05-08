"""
Migration script to add the SyncLog, MonthPeriod, and TempAttendance tables to the database.
This fixes the database error: "cannot import name 'SyncLog' from 'models'"
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import text, create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, Float, Date, Text, ForeignKey
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment or use the default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")

def run_migration():
    """Add the SyncLog, MonthPeriod, and TempAttendance tables if they don't exist"""
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    
    try:
        with engine.connect() as conn:
            # Check if tables exist
            sync_logs_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'sync_logs'
                )
            """)).scalar()
            
            month_periods_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'month_periods'
                )
            """)).scalar()
            
            temp_attendance_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'temp_attendance'
                )
            """)).scalar()
            
            # Create sync_logs table if it doesn't exist
            if not sync_logs_exists:
                logger.info("Creating sync_logs table...")
                
                sync_logs = Table(
                    'sync_logs', 
                    metadata,
                    Column('id', Integer, primary_key=True),
                    Column('sync_time', DateTime, default=datetime.utcnow),
                    Column('status', String(50), default='pending'),
                    Column('step', String(50)),
                    Column('progress', Integer, default=0),
                    Column('message', String(255)),
                    Column('error', Text),
                    Column('departments_synced', String(255)),
                    Column('records_synced', Integer, default=0),
                    Column('created_at', DateTime, default=datetime.utcnow),
                    Column('updated_at', DateTime, default=datetime.utcnow)
                )
                
                sync_logs.create(engine)
                logger.info("sync_logs table created successfully")
            
            # Create month_periods table if it doesn't exist
            if not month_periods_exists:
                logger.info("Creating month_periods table...")
                
                month_periods = Table(
                    'month_periods', 
                    metadata,
                    Column('id', Integer, primary_key=True),
                    Column('month_code', String(10), unique=True),
                    Column('start_date', Date, nullable=False),
                    Column('end_date', Date, nullable=False),
                    Column('days_in_month', Integer, default=30),
                    Column('hours_in_month', Float, default=240.0),
                    Column('created_at', DateTime, default=datetime.utcnow),
                    Column('updated_at', DateTime, default=datetime.utcnow)
                )
                
                month_periods.create(engine)
                logger.info("month_periods table created successfully")
            
            # Create temp_attendance table if it doesn't exist
            if not temp_attendance_exists:
                logger.info("Creating temp_attendance table...")
                
                temp_attendance = Table(
                    'temp_attendance', 
                    metadata,
                    Column('id', Integer, primary_key=True),
                    Column('emp_code', String(20)),
                    Column('first_name', String(100)),
                    Column('last_name', String(100)),
                    Column('dept_name', String(100)),
                    Column('att_date', Date),
                    Column('punch_time', String(20)),
                    Column('punch_state', String(10)),
                    Column('terminal_alias', String(100)),
                    Column('sync_id', Integer),
                    Column('created_at', DateTime, default=datetime.utcnow)
                )
                
                temp_attendance.create(engine)
                logger.info("temp_attendance table created successfully")
            
            logger.info("Migration completed successfully")
            
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"Error occurred during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting migration script to add new tables...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)
