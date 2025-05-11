"""
Cleanup script for the Housing Maintenance application.
This script removes unnecessary files and cleans up the codebase.
"""
import os
import sys
import logging
import time
import shutil
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Files to be removed
UNNECESSARY_FILES = [
    # Backup files
    r".*\.bak$",
    r".*\.bak\.\d+$",
    r".*\.backup$",
    
    # Debug and test files
    r"debug_.*\.py$",
    r"test_.*\.py$",
    r".*_test\.py$",
    r".*_debug\.py$",
    
    # Temporary files
    r".*\.tmp$",
    r".*\.temp$",
    
    # Old optimization files that are now replaced
    r"optimize_.*\.py$",
    r".*_optimization\.py$",
    
    # Specific files to remove
    "clear_cache.py",
    "clear_cache_and_test.py",
    "clear_timesheet_cache.py",
    "check_syncs.py",
    "analyze_remaining_employees.py",
    "fix_documentation.md",
    "fix_report.md",
    "fix_may11_issue_summary.md",
    "optimization_summary.py",
    "patch_util.py",
    "update_template.py",
    "enable_arabic_powershell.ps1"
]

# Directories to clean
CACHE_DIRECTORIES = [
    "instance/cache",
    "__pycache__"
]

# Files to keep even if they match patterns
KEEP_FILES = [
    "optimized_timesheet.py",
    "optimized_data_processor.py",
    "enhanced_cache_optimized.py",
    "performance_optimizer.py",
    "cleanup.py"
]

def should_remove_file(filename):
    """Check if a file should be removed"""
    # Always keep files in the KEEP_FILES list
    if filename in KEEP_FILES:
        return False
    
    # Check if file matches any pattern in UNNECESSARY_FILES
    for pattern in UNNECESSARY_FILES:
        if pattern.startswith(r".*") or pattern.endswith("$"):
            # This is a regex pattern
            if re.match(pattern, filename):
                return True
        elif pattern == filename:
            # This is an exact match
            return True
    
    return False

def clean_directory(directory):
    """Clean a directory by removing unnecessary files"""
    removed_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if should_remove_file(file):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    removed_files.append(file_path)
                    logger.info(f"Removed file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {str(e)}")
    
    return removed_files

def clean_cache_directories():
    """Clean cache directories"""
    for directory in CACHE_DIRECTORIES:
        if os.path.exists(directory):
            try:
                # Remove all files in the directory
                for file in os.listdir(directory):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed cache file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning cache directory {directory}: {str(e)}")

def archive_old_files():
    """Archive old files instead of deleting them"""
    archive_dir = "archived_files"
    os.makedirs(archive_dir, exist_ok=True)
    
    archived_files = []
    
    for root, dirs, files in os.walk("."):
        # Skip the archive directory itself
        if root.startswith(f".{os.sep}{archive_dir}"):
            continue
        
        for file in files:
            if should_remove_file(file):
                src_path = os.path.join(root, file)
                dst_path = os.path.join(archive_dir, file)
                
                # If file already exists in archive, add timestamp
                if os.path.exists(dst_path):
                    timestamp = int(time.time())
                    name, ext = os.path.splitext(file)
                    dst_path = os.path.join(archive_dir, f"{name}_{timestamp}{ext}")
                
                try:
                    shutil.move(src_path, dst_path)
                    archived_files.append((src_path, dst_path))
                    logger.info(f"Archived file: {src_path} -> {dst_path}")
                except Exception as e:
                    logger.error(f"Error archiving file {src_path}: {str(e)}")
    
    return archived_files

def run_cleanup(archive_mode=True):
    """Run the cleanup process"""
    print("=" * 80)
    print("CLEANING UP HOUSING MAINTENANCE APPLICATION")
    print("=" * 80)
    
    if archive_mode:
        print("\nArchiving unnecessary files...")
        archived_files = archive_old_files()
        print(f"\nArchived {len(archived_files)} files to the 'archived_files' directory.")
    else:
        print("\nRemoving unnecessary files...")
        removed_files = clean_directory(".")
        print(f"\nRemoved {len(removed_files)} unnecessary files.")
    
    print("\nCleaning cache directories...")
    clean_cache_directories()
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    # Check if archive mode is specified
    archive_mode = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--delete":
        archive_mode = False
    
    run_cleanup(archive_mode)
