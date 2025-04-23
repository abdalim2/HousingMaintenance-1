"""
Script para actualizar la estructura de la base de datos
Ejecutar una vez para añadir nuevos campos a la tabla sync_logs
"""
import os
import logging
from flask import Flask
from database import db, init_db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_sync_logs_table():
    """Add missing columns to sync_logs table if they don't exist"""
    try:
        # Create a Flask app instance for database connection
        app = Flask(__name__)
        
        # Configure database connection
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "connect_args": {
                "sslmode": "require"
            }
        }
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # Initialize the database
        init_db(app)
        
        with app.app_context():
            # Check if end_time column exists
            sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='sync_logs' AND column_name='end_time';
            """)
            
            result = db.session.execute(sql).fetchone()
            
            if not result:
                # Column doesn't exist, add it
                logger.info("Adding end_time column to sync_logs table")
                sql = text("ALTER TABLE sync_logs ADD COLUMN end_time TIMESTAMP;")
                db.session.execute(sql)
                db.session.commit()
                logger.info("Successfully added end_time column to sync_logs table")
            else:
                logger.info("end_time column already exists in sync_logs table")
            
            # Check if step column exists
            sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='sync_logs' AND column_name='step';
            """)
            
            result = db.session.execute(sql).fetchone()
            
            if not result:
                # Column doesn't exist, add it
                logger.info("Adding step column to sync_logs table")
                sql = text("ALTER TABLE sync_logs ADD COLUMN step VARCHAR(20);")
                db.session.execute(sql)
                db.session.commit()
                logger.info("Successfully added step column to sync_logs table")
            else:
                logger.info("step column already exists in sync_logs table")
        
        return True
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        return False

if __name__ == "__main__":
    if update_sync_logs_table():
        print("Database update completed successfully")
    else:
        print("Database update failed")