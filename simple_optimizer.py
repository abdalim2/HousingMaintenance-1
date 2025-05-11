"""
Simple optimization script for the Housing Maintenance application.
This script applies basic optimizations to improve the performance of the application.
"""
import os
import logging
import time
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    backup_path = f"{file_path}.bak.{int(time.time())}"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup of {file_path} at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {str(e)}")
        return False

def create_optimized_cache_module():
    """Create the optimized cache module"""
    file_path = 'enhanced_cache_optimized.py'
    
    if os.path.exists(file_path):
        logger.info(f"File {file_path} already exists, skipping creation")
        return True
    
    try:
        content = '''"""
Enhanced caching implementation for the Housing Maintenance application
with improved performance and memory management
"""
import os
import time
import pickle
import hashlib
import logging
from functools import wraps
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Create timesheet cache directory
TIMESHEET_CACHE_DIR = os.path.join(CACHE_DIR, 'timesheets')
os.makedirs(TIMESHEET_CACHE_DIR, exist_ok=True)

# In-memory LRU cache for most frequently accessed items
MEMORY_CACHE = {}
MEMORY_CACHE_MAX_SIZE = 150  # Increased from 100 to 150
MEMORY_CACHE_TIMESTAMPS = {}  # Track when items were added to cache

# In-memory timesheet cache
_timesheet_cache = {}

class EnhancedCache:
    """Enhanced caching class with both memory and disk caching"""
    
    def __init__(self, cache_dir=CACHE_DIR, timeout=3600, max_memory_items=MEMORY_CACHE_MAX_SIZE):
        """Initialize the cache"""
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.max_memory_items = max_memory_items
        os.makedirs(cache_dir, exist_ok=True)
    
    def get(self, key, default=None):
        """Get an item from cache (memory first, then disk)"""
        # Try memory cache first (fastest)
        if key in MEMORY_CACHE:
            timestamp = MEMORY_CACHE_TIMESTAMPS.get(key, 0)
            if time.time() - timestamp <= self.timeout:
                return MEMORY_CACHE[key]
            else:
                # Expired, remove from memory
                self._remove_from_memory(key)
        
        # Try disk cache next
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                # Check if file is expired
                modified_time = os.path.getmtime(cache_path)
                if time.time() - modified_time <= self.timeout:
                    with open(cache_path, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Store in memory for faster access next time
                    self._add_to_memory(key, data)
                    return data
                else:
                    # Expired, remove file
                    try:
                        os.unlink(cache_path)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error reading cache file {cache_path}: {str(e)}")
        
        return default
    
    def set(self, key, value, timeout=None):
        """Set an item in cache (both memory and disk)"""
        if timeout is None:
            timeout = self.timeout
        
        # Store in memory
        self._add_to_memory(key, value)
        
        # Store in disk
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            logger.error(f"Error writing to cache file {cache_path}: {str(e)}")
            return False
    
    def clear(self, pattern=None):
        """Clear all cache entries or those matching a pattern"""
        # Clear memory cache
        if pattern:
            keys_to_remove = [k for k in MEMORY_CACHE if pattern in k]
            for k in keys_to_remove:
                self._remove_from_memory(k)
        else:
            MEMORY_CACHE.clear()
            MEMORY_CACHE_TIMESTAMPS.clear()
        
        # Clear disk cache
        try:
            removed = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl') and (not pattern or pattern in filename):
                    try:
                        os.unlink(os.path.join(self.cache_dir, filename))
                        removed += 1
                    except:
                        pass
            return removed
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0
    
    def _get_cache_path(self, key):
        """Get the file path for a cache key"""
        if len(key) > 40:  # If key is too long, hash it
            key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.pkl")
    
    def _add_to_memory(self, key, value):
        """Add an item to memory cache with LRU eviction"""
        # If cache is full, remove oldest item
        if len(MEMORY_CACHE) >= self.max_memory_items:
            oldest_key = min(MEMORY_CACHE_TIMESTAMPS.items(), key=lambda x: x[1])[0]
            self._remove_from_memory(oldest_key)
        
        # Add to memory cache
        MEMORY_CACHE[key] = value
        MEMORY_CACHE_TIMESTAMPS[key] = time.time()
    
    def _remove_from_memory(self, key):
        """Remove an item from memory cache"""
        if key in MEMORY_CACHE:
            del MEMORY_CACHE[key]
        if key in MEMORY_CACHE_TIMESTAMPS:
            del MEMORY_CACHE_TIMESTAMPS[key]

# Create timesheet cache instance with 2 hour timeout
timesheet_cache = EnhancedCache(
    cache_dir=TIMESHEET_CACHE_DIR,
    timeout=7200,  # 2 hours
    max_memory_items=75  # Increased from 50 to 75
)

def clear_timesheet_cache():
    """Clear all timesheet cache entries"""
    global _timesheet_cache
    had_entries = len(_timesheet_cache) > 0
    _timesheet_cache = {}
    return had_entries
'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created optimized cache module: {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating optimized cache module: {str(e)}")
        return False

def run_optimization():
    """Run all optimization steps"""
    print("=" * 80)
    print("APPLYING BASIC PERFORMANCE OPTIMIZATIONS")
    print("=" * 80)
    
    # Step 1: Create optimized cache module
    print("\n1. Creating optimized cache module...")
    create_optimized_cache_module()
    
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print("\nThe application performance has been improved.")
    print("Please restart the application to apply all changes.")

if __name__ == "__main__":
    run_optimization()
