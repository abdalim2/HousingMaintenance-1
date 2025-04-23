"""
Database migration script to add the daily_hours column to the employees table.

Run this script once to update the database schema. This is needed because we added
the daily_hours column to the Employee model in models.py but need to update the 
actual database table.
"""
import os
import sys
import logging
from flask import Flask
from sqlalchemy import text
from database import db, init_db
from models import Employee

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create a Flask app instance for database operations"""
    app = Flask(__name__)
    
    # Use the same database configuration as in app.py
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 15,
        "connect_args": {
            "sslmode": "require"
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the database connection
    init_db(app)
    
    return app

def add_daily_hours_column():
    """Add daily_hours column to employees table if it doesn't exist"""
    try:
        app = create_app()
        with app.app_context():
            conn = db.engine.connect()
            
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('employees')]
            
            if 'daily_hours' in columns:
                logger.info("daily_hours column already exists - no migration needed")
                conn.close()
                return False
            
            # Column doesn't exist, so add it
            logger.info("Adding daily_hours column to employees table...")
            
            # Start a fresh transaction
            try:
                # Create a new clean transaction
                with conn.begin():
                    # Add the column with a default value of 8.0
                    conn.execute(text("ALTER TABLE employees ADD COLUMN daily_hours FLOAT DEFAULT 8.0"))
                    logger.info("Migration completed successfully! daily_hours column added with default value 8.0")
                    return True
            finally:
                conn.close()
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database migration...")
    
    success = add_daily_hours_column()
    
    if success:
        logger.info("Database migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database migration failed or was not needed!")
        sys.exit(1)