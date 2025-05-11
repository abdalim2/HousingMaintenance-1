"""
Script to clear the cache and test timesheet generation directly
"""

import os
import logging
import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_cache_directory():
    """Clear the disk cache directory"""
    try:
        # Import the cache manager to get the cache directory
        from enhanced_cache import CACHE_DIR
        
        if os.path.exists(CACHE_DIR):
            logger.info(f"Clearing cache directory: {CACHE_DIR}")
            # Delete all .cache files in the directory
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith(".cache"):
                    file_path = os.path.join(CACHE_DIR, filename)
                    try:
                        os.unlink(file_path)
                        logger.info(f"Deleted cache file: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting file {filename}: {str(e)}")
        else:
            logger.info(f"Cache directory does not exist: {CACHE_DIR}")
            
        return True
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return False

def test_timesheet_generation():
    """Test generating timesheet data directly"""
    try:
        # Import necessary modules
        from optimized_timesheet import optimized_generate_timesheet
        from app import app
        
        # Get current year and month
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        
        logger.info(f"Testing timesheet generation for {year}/{month}")
        
        # Create an application context
        with app.app_context():
            # Try to generate the timesheet with force_refresh=True
            timesheet_data = optimized_generate_timesheet(
                year=year, 
                month=month, 
                department_id=None,
                custom_start_date=None, 
                custom_end_date=None,
                housing_id=None, 
                limit=10, 
                offset=0, 
                force_refresh=True
            )
        
        if timesheet_data:
            logger.info(f"Successfully generated timesheet data with {len(timesheet_data.get('employees', []))} employees")
            # Check if there are any employees in the data
            if not timesheet_data.get('employees'):
                logger.warning("No employees found in the generated timesheet data")
            return True
        else:
            logger.error("Failed to generate timesheet data, result is None or empty")
            return False
            
    except Exception as e:
        logger.error(f"Error testing timesheet generation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting cache clearing and timesheet test...")
    
    # Clear the cache
    if clear_cache_directory():
        logger.info("Cache cleared successfully")
    else:
        logger.error("Failed to clear cache")
    
    # Test timesheet generation
    if test_timesheet_generation():
        logger.info("Timesheet generation test successful")
        sys.exit(0)
    else:
        logger.error("Timesheet generation test failed")
        sys.exit(1)
