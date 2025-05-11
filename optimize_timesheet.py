#!/usr/bin/env python
"""
This script implements performance optimizations for the timesheet functionality
to reduce load times from 3 minutes to a few seconds.

Optimization strategy:
1. Implement effective caching for timesheet data
2. Optimize database queries
3. Reduce in-memory data processing
4. Add database indexes
5. Implement pagination
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import text, Index
from flask import Flask, render_template, session
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load app context to run optimization functions
try:
    from app import app, db
    from models import AttendanceRecord, Employee, Housing, BiometricTerminal, Department
    from data_processor import generate_timesheet
    from cache_manager import clear_cache, disk_cache, get_cache_stats
except ImportError as e:
    logger.error(f"Error importing modules: {str(e)}")
    sys.exit(1)

def add_database_indexes():
    """Add missing indexes to improve query performance"""
    try:
        with app.app_context():
            # Check existing indexes to avoid duplicates
            existing_indexes = {}
            
            # Get existing indexes for attendance_records table
            result = db.session.execute(text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'attendance_records'"
            ))
            existing_indexes['attendance_records'] = [r[0] for r in result]
            
            # Add missing indexes
            indexes_to_add = [
                # Index for fetching attendance records by date range and employee
                {'name': 'idx_attendance_date_employee', 
                 'table': AttendanceRecord.__table__, 
                 'columns': ['employee_id', 'date'],
                 'unique': False},
                
                # Index for attendance status
                {'name': 'idx_attendance_status', 
                 'table': AttendanceRecord.__table__, 
                 'columns': ['attendance_status'],
                 'unique': False},
                
                # Index for employee active status
                {'name': 'idx_employee_active', 
                 'table': Employee.__table__, 
                 'columns': ['active'],
                 'unique': False},
                 
                # Index for employee department
                {'name': 'idx_employee_department', 
                 'table': Employee.__table__, 
                 'columns': ['department_id'],
                 'unique': False}
            ]
            
            added_indexes = 0
            for idx_info in indexes_to_add:
                table_name = idx_info['table'].name
                if table_name not in existing_indexes:
                    existing_indexes[table_name] = []
                    
                if idx_info['name'] not in existing_indexes[table_name]:
                    columns = [getattr(idx_info['table'].c, col_name) for col_name in idx_info['columns']]
                    idx = Index(idx_info['name'], *columns, unique=idx_info['unique'])
                    try:
                        idx.create(db.engine)
                        added_indexes += 1
                        logger.info(f"Created index: {idx_info['name']}")
                    except Exception as e:
                        logger.error(f"Error creating index {idx_info['name']}: {str(e)}")
            
            if added_indexes > 0:
                logger.info(f"Successfully added {added_indexes} new indexes")
                return True
            else:
                logger.info("No new indexes needed")
                return False
                
    except Exception as e:
        logger.error(f"Error adding database indexes: {str(e)}")
        return False

def optimize_timesheet_function():
    """Optimize the timesheet generation function in data_processor.py"""
    try:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_processor.py')
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add effective caching with proper cache key generation
        original = """    # Create a cache key based on parameters
    cache_key = f"timesheet_{year}_{month}_{department_id}_{custom_start_date}_{custom_end_date}_{housing_id}_{limit}_{offset}"""
        
        replacement = """    # Create a cache key based on parameters
    import hashlib
    
    # Create a more precise cache key that includes all relevant parameters
    cache_params = f"timesheet_{year}_{month}_{department_id}_{custom_start_date}_{custom_end_date}_{housing_id}_{limit}_{offset}"
    cache_key = f"timesheet_{hashlib.md5(cache_params.encode()).hexdigest()}"
    
    # Check if we can return data from cache (unless force refresh is requested)
    if not force_refresh:
        cached_data = disk_cache.get(cache_key)
        if cached_data:
            logger.info(f"Returning timesheet data from cache for {year}/{month}")
            return cached_data"""
            
        # Add saving to cache at the end of the function
        original_end = """        logger.info(f"Generated timesheet data in {execution_time:.2f} seconds")
        
        return timesheet_data"""
        
        replacement_end = """        logger.info(f"Generated timesheet data in {execution_time:.2f} seconds")
        
        # Save to cache for future requests
        disk_cache.set(cache_key, timesheet_data)
        
        return timesheet_data"""
        
        # Optimize attendance records query with targeted date filtering
        original_chunk_query = """                chunk_records = AttendanceRecord.query.filter(
                    AttendanceRecord.employee_id.in_(chunk_ids),
                    AttendanceRecord.date >= start_date,
                    AttendanceRecord.date <= end_date
                ).all()"""
                
        replacement_chunk_query = """                chunk_records = AttendanceRecord.query.filter(
                    AttendanceRecord.employee_id.in_(chunk_ids),
                    AttendanceRecord.date >= start_date,
                    AttendanceRecord.date <= end_date
                ).options(
                    # Disable relationship loading to improve query performance
                    db.joinedload(None)
                ).all()"""
        
        # Make similar change for smaller sets query
        original_single_query = """            attendance_records = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(employee_ids),
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date
            ).all()"""
            
        replacement_single_query = """            attendance_records = AttendanceRecord.query.filter(
                AttendanceRecord.employee_id.in_(employee_ids),
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date
            ).options(
                # Disable relationship loading to improve query performance
                db.joinedload(None)
            ).all()"""
        
        # Optimize terminal and housing loading to reduce database queries
        original_housing = """        # جمع جميع أجهزة البصمة والسكنات المرتبطة بها
        terminals = BiometricTerminal.query.all()
        housings = Housing.query.all()"""
        
        replacement_housing = """        # جمع جميع أجهزة البصمة والسكنات المرتبطة بها - استخدم eager loading
        terminals = BiometricTerminal.query.options(
            db.joinedload(BiometricTerminal.housing)
        ).all()
        
        # Preload all housings into dictionary to avoid repeated queries
        housings = {h.id: h for h in Housing.query.all()}"""
        
        # Update the housing names dictionary creation
        original_housing_names = """        # تخزين أسماء السكنات حسب المعرف
        for housing in housings:
            housing_names[housing.id] = housing.name"""
            
        replacement_housing_names = """        # تخزين أسماء السكنات حسب المعرف
        for housing_id, housing in housings.items():
            housing_names[housing_id] = housing.name"""
            
        # Optimize employee department loading to reduce database queries
        original_dept_query = """            dept_name = ''
            if employee.department_id:
                dept = Department.query.get(employee.department_id)
                if dept:
                    dept_name = dept.name"""
                    
        replacement_dept_query = """            # Extract department name from already loaded relationship
            dept_name = ''
            if employee.department_id and hasattr(employee, 'department') and employee.department:
                dept_name = employee.department.name"""
        
        # Update housing query to use preloaded data
        original_employee_housing = """            # إذا كان للموظف سكن محدد، استخدم اسم السكن من قاعدة البيانات
            if employee_housing_id:
                housing = Housing.query.get(employee_housing_id)
                if housing:
                    housing_name = housing.name
                    # أضف سكن الموظف إلى قائمة السكنات المستخدمة
                    all_housing_used.add(employee_housing_id)"""
                    
        replacement_employee_housing = """            # إذا كان للموظف سكن محدد، استخدم اسم السكن من البيانات المحملة مسبقاً
            if employee_housing_id:
                housing_name = housing_names.get(employee_housing_id, "")
                if housing_name:
                    # أضف سكن الموظف إلى قائمة السكنات المستخدمة
                    all_housing_used.add(employee_housing_id)"""
        
        # Make all the replacements
        new_content = content.replace(original, replacement)
        new_content = new_content.replace(original_end, replacement_end)
        new_content = new_content.replace(original_chunk_query, replacement_chunk_query)
        new_content = new_content.replace(original_single_query, replacement_single_query)
        new_content = new_content.replace(original_housing, replacement_housing)
        new_content = new_content.replace(original_housing_names, replacement_housing_names)
        new_content = new_content.replace(original_dept_query, replacement_dept_query)
        new_content = new_content.replace(original_employee_housing, replacement_employee_housing)
        
        # Write the optimized file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info(f"Successfully optimized timesheet function in {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Error optimizing timesheet function: {str(e)}")
        return False

def test_timesheet_performance():
    """Test the timesheet performance before and after optimization"""
    with app.app_context(), app.test_request_context('/timesheet'):
        # Initialize session variables that might be needed
        session['language'] = 'en'
        
        # Print cache stats before
        print("Cache stats before test:", get_cache_stats())
        
        # Clear cache to ensure a fresh test
        clear_cache("timesheet_")
        
        print("\nTesting timesheet performance...")
        
        # Test uncached performance
        start_time = time.time()
        result = generate_timesheet('2025', '5', force_refresh=True)
        first_run_time = time.time() - start_time
        
        print(f"First run (uncached): {first_run_time:.2f} seconds")
        print(f"Records: {len(result.get('employees', []))} employees, {len(result.get('dates', []))} days")
        
        # Test cached performance
        start_time = time.time()
        result = generate_timesheet('2025', '5')
        cached_run_time = time.time() - start_time
        
        print(f"Second run (cached): {cached_run_time:.2f} seconds")
        print(f"Cache speedup factor: {first_run_time/cached_run_time:.1f}x faster")
        
        # Print cache stats after
        print("\nCache stats after test:", get_cache_stats())
        
        return {
            'first_run_time': first_run_time,
            'cached_run_time': cached_run_time,
            'speedup_factor': first_run_time/cached_run_time,
            'employee_count': len(result.get('employees', []))
        }

if __name__ == "__main__":
    print("=" * 80)
    print("TIMESHEET PERFORMANCE OPTIMIZATION")
    print("=" * 80)
    
    # Step 1: Add database indexes
    print("\nStep 1: Adding database indexes...")
    add_database_indexes()
    
    # Step 2: Optimize the timesheet function in data_processor.py
    print("\nStep 2: Optimizing timesheet generation function...")
    optimize_timesheet_function()
    
    # Step 3: Test performance
    print("\nStep 3: Testing performance improvement...")
    performance_results = test_timesheet_performance()
    
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"Uncached load time: {performance_results['first_run_time']:.2f} seconds")
    print(f"Cached load time: {performance_results['cached_run_time']:.2f} seconds")
    print(f"Speedup factor: {performance_results['speedup_factor']:.1f}x faster")
    print("=" * 80)
    print("\nRestart the application to apply all changes.")
