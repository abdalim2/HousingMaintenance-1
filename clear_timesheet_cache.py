"""
Script to clear the timesheet cache and force fresh data generation.
This helps resolve DetachedInstanceError issues by ensuring no stale SQLAlchemy objects
are stored in the cache.
"""

from app import app
import logging
from enhanced_cache import clear_timesheet_cache
from flask import Flask

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

with app.app_context():
    try:
        # Clear all timesheet cache entries
        cleared = clear_timesheet_cache()
        if cleared:
            logger.info("✓ Successfully cleared timesheet cache")
        else:
            logger.warning("! No timesheet cache entries found to clear")
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        import traceback
        traceback.print_exc()
