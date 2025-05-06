"""
Migration script to add terminal_id_in and terminal_id_out columns to attendance_records table.
This fixes the database error: 'column attendance_records.terminal_id_in does not exist'
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
    """Add the terminal_id columns to attendance_records table if they don't exist"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if terminal_id_in column exists
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='attendance_records' AND column_name='terminal_id_in'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding terminal_id_in column to attendance_records table...")
                
                # Add terminal_id_in column as nullable integer with foreign key constraint
                add_column_sql = text("""
                    ALTER TABLE attendance_records 
                    ADD COLUMN terminal_id_in INTEGER,
                    ADD CONSTRAINT fk_attendance_terminal_in 
                    FOREIGN KEY (terminal_id_in) REFERENCES biometric_terminals(id)
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added terminal_id_in column to attendance_records table")
                
            # Check if terminal_id_out column exists
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='attendance_records' AND column_name='terminal_id_out'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding terminal_id_out column to attendance_records table...")
                
                # Add terminal_id_out column as nullable integer with foreign key constraint
                add_column_sql = text("""
                    ALTER TABLE attendance_records 
                    ADD COLUMN terminal_id_out INTEGER,
                    ADD CONSTRAINT fk_attendance_terminal_out 
                    FOREIGN KEY (terminal_id_out) REFERENCES biometric_terminals(id)
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added terminal_id_out column to attendance_records table")
                
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Error performing migration: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database migration...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)