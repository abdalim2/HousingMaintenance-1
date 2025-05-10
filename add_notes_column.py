import os
import sys
from sqlalchemy import create_engine, text
from database import db
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_notes_column():
    """
    Add notes column to attendance_records table
    """
    try:
        # Check if the column already exists
        check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name = 'attendance_records' AND column_name = 'notes';")
        result = db.session.execute(check_sql).fetchone()
        
        if result:
            logger.info("'notes' column already exists in attendance_records table. No changes needed.")
            return
            
        # Add the notes column
        alter_sql = text("ALTER TABLE attendance_records ADD COLUMN notes TEXT;")
        db.session.execute(alter_sql)
        db.session.commit()
        
        logger.info("Successfully added 'notes' column to attendance_records table.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding 'notes' column: {str(e)}")
        raise

if __name__ == "__main__":
    from app import app
    with app.app_context():
        add_notes_column()
        logger.info("Migration completed.")
