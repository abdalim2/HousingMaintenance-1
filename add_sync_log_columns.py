"""
Script to add the required columns to the SyncLog model in the database.

This script adds the following columns if they don't exist:
- progress (INTEGER)
- step (VARCHAR)
- message (VARCHAR)
- error (TEXT)
- departments_synced (VARCHAR)
- records_synced (INTEGER)
- status (VARCHAR)
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment or use the default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")

# Log start message
logger.info("Starting update of sync_logs table...")

def run_migration():
    """Add the required columns to sync_logs table if they don't exist"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if progress column exists in sync_logs
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='sync_logs' AND column_name='progress'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding progress column to sync_logs table...")
                
                add_column_sql = text("""
                    ALTER TABLE sync_logs 
                    ADD COLUMN progress INTEGER DEFAULT 0
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added progress column to sync_logs table")
            
            # Check for other required columns
            for column, column_type, default in [
                ('step', 'VARCHAR(50)', 'NULL'),
                ('message', 'VARCHAR(255)', 'NULL'),
                ('error', 'TEXT', 'NULL'),
                ('departments_synced', 'VARCHAR(255)', 'NULL'),
                ('records_synced', 'INTEGER', '0'),
                ('status', 'VARCHAR(50)', "'pending'")
            ]:
                check_sql = text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name='sync_logs' AND column_name='{column}'
                """)
                
                result = conn.execute(check_sql)
                if result.rowcount == 0:
                    logger.info(f"Adding {column} column to sync_logs table...")
                    
                    add_column_sql = text(f"""
                        ALTER TABLE sync_logs 
                        ADD COLUMN {column} {column_type} DEFAULT {default}
                    """)
                    
                    conn.execute(add_column_sql)
                    conn.commit()
                    logger.info(f"Successfully added {column} column to sync_logs table")
                
            logger.info("Migration completed successfully")
            
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"Error occurred during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting migration script to add missing columns to sync_logs table...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)