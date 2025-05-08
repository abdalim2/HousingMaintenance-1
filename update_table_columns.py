"""
Migration script to update the month_periods table to add the missing columns.
"""

import os
import sys
import logging
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment or use the default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require")

def run_migration():
    """Update the month_periods table to add missing columns"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if created_at column exists in month_periods
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='month_periods' AND column_name='created_at'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding created_at column to month_periods table...")
                
                add_column_sql = text("""
                    ALTER TABLE month_periods 
                    ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added created_at column to month_periods table")
            
            # Check if updated_at column exists in month_periods
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='month_periods' AND column_name='updated_at'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding updated_at column to month_periods table...")
                
                add_column_sql = text("""
                    ALTER TABLE month_periods 
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added updated_at column to month_periods table")
            
            # Check if sync_logs table has all the expected columns
            for column in ['created_at', 'updated_at']:
                check_sql = text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name='sync_logs' AND column_name='{column}'
                """)
                
                result = conn.execute(check_sql)
                if result.rowcount == 0:
                    logger.info(f"Adding {column} column to sync_logs table...")
                    
                    add_column_sql = text(f"""
                        ALTER TABLE sync_logs 
                        ADD COLUMN {column} TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    logger.info("Starting migration script to update tables with missing columns...")
    success = run_migration()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)
