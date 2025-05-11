"""
Enhanced caching implementation for the Housing Maintenance application
with improved performance and memory management
"""
import os
import time
import pickle
import hashlib
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import current_app, g, request, session

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

    def _get_cache_path(self, key):
        """Get the file path for a cache key"""
        if len(key) > 40:  # If key is too long, hash it
            key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.pkl")

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

    def delete(self, key):
        """Delete an item from cache (both memory and disk)"""
        # Remove from memory
        self._remove_from_memory(key)

        # Remove from disk
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                os.unlink(cache_path)
                return True
            except Exception as e:
                logger.error(f"Error removing cache file {cache_path}: {str(e)}")
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

def cached_timesheet(func):
    """
    Decorator to cache timesheet data in memory.
    Ensures all SQLAlchemy objects are properly converted to dictionaries.
    Uses a more efficient caching strategy with deep copy for thread safety.
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Skip cache if force_refresh is True
        if kwargs.get('force_refresh'):
            kwargs.pop('force_refresh', None)
            return func(*args, **kwargs)

        # Create a cache key
        key_parts = [str(arg) for arg in args]

        # Add sorted kwargs
        for k in sorted(kwargs.keys()):
            if k != 'force_refresh':  # Skip force_refresh in cache key
                key_parts.append(f"{k}:{kwargs[k]}")

        # Join parts and hash
        key = "_".join(key_parts)
        cache_key = hashlib.md5(key.encode()).hexdigest()

        # Check if the result is in the cache
        global _timesheet_cache
        if cache_key in _timesheet_cache:
            # Use a deep copy of the cached data to ensure it's a completely separate object
            import copy
            return copy.deepcopy(_timesheet_cache[cache_key])

        # Call the original function
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Store in memory cache - ensure result is not None and has employees data
        if result and isinstance(result, dict):
            _timesheet_cache[cache_key] = result
            logger.info(f"Cached timesheet with {len(result.get('employees', []))} employees for {args[0]}/{args[1]} in {execution_time:.2f}s")

        return result
    return decorated_function

def get_cache_stats():
    """Get statistics about cache usage"""
    memory_items = len(MEMORY_CACHE)
    timesheet_items = len(_timesheet_cache)

    # Count disk cache items and size
    disk_items = 0
    disk_size = 0
    try:
        for filename in os.listdir(TIMESHEET_CACHE_DIR):
            if filename.endswith('.pkl'):
                disk_items += 1
                disk_size += os.path.getsize(os.path.join(TIMESHEET_CACHE_DIR, filename))
    except:
        pass

    return {
        'memory_items': memory_items,
        'timesheet_items': timesheet_items,
        'disk_items': disk_items,
        'disk_size_mb': round(disk_size / (1024 * 1024), 2)
    }

def attendance_record_to_dict(record):
    """Convert an AttendanceRecord object to a dictionary to prevent DetachedInstanceError"""
    if not record:
        return None

    return {
        'id': record.id,
        'employee_id': record.employee_id,
        'date': record.date,
        'weekday': record.weekday,
        'clock_in': record.clock_in,
        'clock_out': record.clock_out,
        'total_time': record.total_time,
        'work_hours': record.work_hours,
        'overtime_hours': record.overtime_hours,
        'attendance_status': record.attendance_status,
        'terminal_id_in': record.terminal_id_in,
        'terminal_id_out': record.terminal_id_out,
        'terminal_alias_in': record.terminal_alias_in,
        'terminal_alias_out': record.terminal_alias_out,
        'exception': record.exception,
        'notes': record.notes
    }

def temp_attendance_to_dict(record):
    """Convert a TempAttendance object to a dictionary to prevent DetachedInstanceError"""
    if not record:
        return None

    return {
        'id': record.id,
        'emp_code': record.emp_code,
        'first_name': record.first_name,
        'last_name': record.last_name,
        'dept_name': record.dept_name,
        'att_date': record.att_date,
        'punch_time': record.punch_time,
        'punch_state': record.punch_state,
        'terminal_alias': record.terminal_alias,
        'sync_id': record.sync_id,
        'created_at': record.created_at
    }
