"""
Migration script to add housing_id column to employees table.
This fixes the database error: 'column employees.housing_id does not exist'
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
    """Add the housing_id column to employees table if it doesn't exist"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if housing_id column exists
            check_sql = text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='employees' AND column_name='housing_id'
            """)
            
            result = conn.execute(check_sql)
            if result.rowcount == 0:
                # Column doesn't exist, add it
                logger.info("Adding housing_id column to employees table...")
                
                # Add housing_id column as nullable integer with foreign key constraint
                add_column_sql = text("""
                    ALTER TABLE employees 
                    ADD COLUMN housing_id INTEGER,
                    ADD CONSTRAINT fk_employees_housing 
                    FOREIGN KEY (housing_id) REFERENCES housings(id)
                """)
                
                conn.execute(add_column_sql)
                conn.commit()
                logger.info("Successfully added housing_id column to employees table")
            else:
                logger.info("housing_id column already exists in employees table")
                
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