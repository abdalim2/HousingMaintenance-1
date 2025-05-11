"""
تحسين أداء تطبيق Housing Maintenance باستخدام التخزين المؤقت (Caching)
Enhanced with disk caching and advanced functionality
"""

import logging
import time
import pickle
import hashlib
import os
from functools import lru_cache, wraps
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create cache directory for persistent caching
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Simple in-memory cache (dictionary)
_MEMORY_CACHE = {}

# DiskCache class that can be instantiated and used as an object
class DiskCache:
    """A class that provides disk-based caching functionality"""
    
    def __init__(self, cache_dir=CACHE_DIR, expire_seconds=3600):
        """Initialize the disk cache
        
        Args:
            cache_dir: Directory to store cache files
            expire_seconds: Time in seconds before cache entries expire
        """
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_file(self, key):
        """Get the cache file path for a given key"""
        # Ensure key is safe for file system
        safe_key = hashlib.md5(str(key).encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.pkl")
    
    def get(self, key):
        """Get a value from the cache
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        cache_file = self._get_cache_file(key)
        
        if os.path.exists(cache_file):
            try:
                # Check if file is expired
                file_mtime = os.path.getmtime(cache_file)
                if time.time() - file_mtime < self.expire_seconds:
                    with open(cache_file, 'rb') as f:
                        result = pickle.load(f)
                    logger.debug(f"Disk cache hit for {key}")
                    return result
                else:
                    # Remove expired file
                    try:
                        os.remove(cache_file)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {str(e)}")
        
        return None
    
    def set(self, key, value):
        """Set a value in the cache
        
        Args:
            key: The cache key
            value: The value to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_file = self._get_cache_file(key)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            logger.debug(f"Saved to disk cache: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving to cache file {cache_file}: {str(e)}")
            return False
    
    def clear(self, pattern=None):
        """Clear cache entries
        
        Args:
            pattern: Optional pattern to match cache keys
            
        Returns:
            Number of entries cleared
        """
        try:
            count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl') and (not pattern or pattern in filename):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                        count += 1
                    except:
                        pass
            logger.info(f"Cleared {count} disk cache files")
            return count
        except Exception as e:
            logger.error(f"Error clearing disk cache: {str(e)}")
            return 0

# Create a global instance of DiskCache for the timesheet
disk_cache = DiskCache(expire_seconds=7200)  # 2 hours expiry

# نموذج لإدارة ذاكرة التخزين المؤقت مع معرف المستخدم
class TimedCache:
    """
    A simple cache that expires entries after a given timeout.
    
    Attributes:
        timeout (int): Number of seconds before entries expire
        cache (dict): In-memory cache storage 
        timestamps (dict): Timestamps for each key to track expiration
    """
    
    def __init__(self, timeout=3600):  # Default timeout of 1 hour
        self.timeout = timeout
        self.cache = {}
        self.timestamps = {}
        
    def get(self, key):
        """Get a value from the cache if it exists and is not expired."""
        if key in self.cache:
            # Check if entry is expired
            if time.time() - self.timestamps[key] > self.timeout:
                # Remove expired entry
                del self.cache[key]
                del self.timestamps[key]
                return None
            return self.cache[key]
        return None
    
    def set(self, key, value):
        """Set a value in the cache with current timestamp."""
        self.cache[key] = value
        self.timestamps[key] = time.time()
        
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()
        
    def clear_expired(self):
        """Clear only expired entries."""
        now = time.time()
        expired_keys = [k for k, t in self.timestamps.items() if now - t > self.timeout]
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]

def generate_cache_key(*args, **kwargs):
    """Generate a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    # Create a hash of the combined arguments
    key_str = ':'.join(key_parts)
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()

def memoize(expire_seconds=300):
    """In-memory cache decorator with expiry"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function name and arguments
            cache_key = f"{func.__module__}.{func.__name__}:{generate_cache_key(*args, **kwargs)}"
            
            # Check if we have a valid cached value
            if cache_key in _MEMORY_CACHE:
                timestamp, result = _MEMORY_CACHE[cache_key]
                if timestamp + expire_seconds > time.time():
                    logger.debug(f"Cache hit for {cache_key}")
                    return result
            
            # If not cached or expired, execute the function
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            _MEMORY_CACHE[cache_key] = (time.time(), result)
            logger.info(f"Cached result for {func.__name__} (took {execution_time:.2f}s)")
            return result
            
        return wrapper
    return decorator

def disk_cache_decorator(expire_seconds=3600, force_refresh=False):
    """Persistent disk cache decorator with expiry"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract force refresh parameter if present
            local_force_refresh = kwargs.pop('force_refresh', force_refresh)
            
            # Generate a unique cache key based on function name and arguments
            cache_key = f"{func.__module__}.{func.__name__}:{generate_cache_key(*args, **kwargs)}"
            safe_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(CACHE_DIR, f"{safe_key}.pkl")
            
            # Check if requested to ignore cache or cache doesn't exist
            if not local_force_refresh:
                # Try to load from cache if file exists and is not expired
                try:
                    if os.path.exists(cache_file):
                        file_mtime = os.path.getmtime(cache_file)
                        if time.time() - file_mtime < expire_seconds:
                            with open(cache_file, 'rb') as f:
                                result = pickle.load(f)
                            logger.debug(f"Disk cache hit for {func.__name__}")
                            return result
                except Exception as e:
                    logger.warning(f"Error reading cache file {cache_file}: {str(e)}")
            
            # Execute the function
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Save result to cache file
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(result, f)
                logger.info(f"Cached {func.__name__} to disk (took {execution_time:.2f}s)")
            except Exception as e:
                logger.error(f"Error saving to cache file {cache_file}: {str(e)}")
            
            return result
            
        return wrapper
    return decorator

def clear_cache(pattern=None):
    """Clear all cache entries or those matching the pattern"""
    # Clear in-memory cache
    if pattern:
        keys_to_remove = [k for k in _MEMORY_CACHE if pattern in k]
        for k in keys_to_remove:
            del _MEMORY_CACHE[k]
        logger.info(f"Cleared {len(keys_to_remove)} memory cache entries matching {pattern}")
    else:
        count = len(_MEMORY_CACHE)
        _MEMORY_CACHE.clear()
        logger.info(f"Cleared all {count} memory cache entries")
    
    # Clear disk cache
    try:
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')]
        removed = 0
        
        for cache_file in cache_files:
            if not pattern or pattern in cache_file:
                try:
                    os.remove(os.path.join(CACHE_DIR, cache_file))
                    removed += 1
                except Exception as e:
                    logger.error(f"Error removing cache file {cache_file}: {str(e)}")
        
        logger.info(f"Cleared {removed} disk cache files")
    except Exception as e:
        logger.error(f"Error accessing cache directory: {str(e)}")

def get_cache_stats():
    """Get statistics about the cache"""
    memory_cache_count = len(_MEMORY_CACHE)
    
    try:
        disk_cache_count = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.pkl')])
        disk_cache_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in os.listdir(CACHE_DIR) if f.endswith('.pkl'))
    except:
        disk_cache_count = 0
        disk_cache_size = 0
    
    return {
        'memory_cache_entries': memory_cache_count,
        'disk_cache_entries': disk_cache_count, 
        'disk_cache_size_mb': round(disk_cache_size / (1024 * 1024), 2)
    }

# تخزين مؤقت للبيانات المستخدمة بشكل متكرر
housing_cache = TimedCache(timeout=1800)  # 30 دقيقة
department_cache = TimedCache(timeout=1800)  # 30 دقيقة

# تخزين مؤقت لبيانات الاجازات والتنقلات
vacation_cache = TimedCache(timeout=300)  # 5 دقائق
transfer_cache = TimedCache(timeout=300)  # 5 دقائق

@lru_cache(maxsize=32)  # تخزين مؤقت لحد 32 استدعاء للدالة
def get_housing_by_id(housing_id):
    """
    Get housing by ID with caching
    """
    from models import Housing
    
    # Check cache first
    cache_key = f"housing_{housing_id}"
    cached_housing = housing_cache.get(cache_key)
    if cached_housing:
        return cached_housing
    
    # If not in cache, get from database and cache
    housing = Housing.query.get(housing_id)
    housing_cache.set(cache_key, housing)
    return housing

@lru_cache(maxsize=32)
def get_department_by_id(dept_id):
    """
    Get department by ID with caching
    """
    from models import Department
    
    # Check cache first
    cache_key = f"dept_{dept_id}"
    cached_dept = department_cache.get(cache_key)
    if cached_dept:
        return cached_dept
    
    # If not in cache, get from database and cache
    dept = Department.query.get(dept_id)
    department_cache.set(cache_key, dept)
    return dept

def get_employee_vacations(employee_id, start_date, end_date):
    """
    Get employee vacations with caching
    """
    from models import EmployeeVacation
    
    # Create cache key based on parameters
    cache_key = f"vacation_{employee_id}_{start_date}_{end_date}"
    
    # Check cache first
    cached_vacations = vacation_cache.get(cache_key)
    if cached_vacations:
        return cached_vacations
    
    # If not in cache, get from database and cache
    vacations = EmployeeVacation.query.filter(
        EmployeeVacation.employee_id == employee_id,
        EmployeeVacation.start_date <= end_date,
        EmployeeVacation.end_date >= start_date
    ).all()
    
    vacation_cache.set(cache_key, vacations)
    return vacations

def get_employee_transfers(employee_id, start_date, end_date):
    """
    Get employee transfers with caching
    """
    from models import EmployeeTransfer
    
    # Create cache key based on parameters
    cache_key = f"transfer_{employee_id}_{start_date}_{end_date}"
    
    # Check cache first
    cached_transfers = transfer_cache.get(cache_key)
    if cached_transfers:
        return cached_transfers
    
    # If not in cache, get from database and cache
    transfers = EmployeeTransfer.query.filter(
        EmployeeTransfer.employee_id == employee_id,
        EmployeeTransfer.start_date <= end_date,
        EmployeeTransfer.end_date >= start_date
    ).all()
    
    transfer_cache.set(cache_key, transfers)
    return transfers

# Function to clear all caches
def clear_all_caches():
    """Clear all application caches"""
    housing_cache.clear()
    department_cache.clear()
    vacation_cache.clear()
    transfer_cache.clear()
    
    # Also clear LRU caches
    get_housing_by_id.cache_clear()
    get_department_by_id.cache_clear()
    
    logger.info("تم مسح جميع ذاكرة التخزين المؤقت")

# Function to periodically clear expired entries
def clear_expired_cache_entries():
    """Clear expired cache entries"""
    housing_cache.clear_expired()
    department_cache.clear_expired()
    vacation_cache.clear_expired()
    transfer_cache.clear_expired()
    
    logger.info("تم مسح مدخلات التخزين المؤقت المنتهية الصلاحية")

# Initialize cache
if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")
    except Exception as e:
        logger.error(f"Failed to create cache directory {CACHE_DIR}: {str(e)}")
