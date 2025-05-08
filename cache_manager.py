"""
تحسين أداء تطبيق Housing Maintenance باستخدام التخزين المؤقت (Caching)
"""

import logging
import time
from functools import lru_cache
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
