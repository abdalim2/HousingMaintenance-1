"""
Migration script to add is_synced and sync_id columns to attendance_records table.
This fixes the database error: 'is_synced is an invalid keyword argument for AttendanceRecord'
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment or use the default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")

def run_migration():
    """Add the is_synced and sync_id columns to attendance_records table if they don't exist"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if is_synced column exists
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='attendance_records' AND column_name='is_synced'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding is_synced column to attendance_records table...")
                
                # Add is_synced column as boolean with default value False
                add_column_sql = text("""
                    ALTER TABLE attendance_records 
                    ADD COLUMN is_synced BOOLEAN DEFAULT FALSE
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added is_synced column to attendance_records table")
            
            # Check if sync_id column exists
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='attendance_records' AND column_name='sync_id'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding sync_id column to attendance_records table...")
                
                # Add sync_id column as nullable integer
                add_column_sql = text("""
                    ALTER TABLE attendance_records 
                    ADD COLUMN sync_id INTEGER
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added sync_id column to attendance_records table")
                
            logger.info("Migration completed successfully")
            
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"Error occurred during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting migration script to add sync columns...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)
