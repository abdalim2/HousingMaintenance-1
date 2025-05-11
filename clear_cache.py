from flask import Flask
import os
import shutil
from database import db
import logging

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://neondb_owner:npg_rj0wp9bMRXox@ep-odd-cherry-a5lefri9-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_timesheet_cache():
    """Clear all timesheet cache files and memory cache"""
    print("Clearing timesheet cache...")
    
    # Clear in-memory cache
    try:
        from enhanced_cache import _timesheet_cache
        cache_size = len(_timesheet_cache)
        _timesheet_cache.clear()
        print(f"Cleared in-memory timesheet cache ({cache_size} entries)")
    except (ImportError, AttributeError) as e:
        print(f"Error clearing in-memory cache: {str(e)}")
    
    # Clear disk cache if it exists
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cache')
    timesheet_cache_dir = os.path.join(cache_dir, 'timesheets')
    
    if os.path.exists(timesheet_cache_dir):
        try:
            # Remove all files in the directory
            for file in os.listdir(timesheet_cache_dir):
                file_path = os.path.join(timesheet_cache_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"Deleted cache file: {file}")
            print(f"Cleared disk cache in {timesheet_cache_dir}")
        except Exception as e:
            print(f"Error clearing disk cache: {str(e)}")
    else:
        print(f"Disk cache directory does not exist: {timesheet_cache_dir}")
    
    print("Cache clearing completed!")

if __name__ == "__main__":
    with app.app_context():
        clear_timesheet_cache()
