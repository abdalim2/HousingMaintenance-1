"""
Installation script for Housing Maintenance application optimizations.
This script applies all optimizations and improvements to the application.
"""
import os
import sys
import logging
import time
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command):
    """Run a command and return its output"""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_python_version():
    """Check if Python version is compatible"""
    import platform
    version = platform.python_version_tuple()
    major, minor = int(version[0]), int(version[1])
    
    if major < 3 or (major == 3 and minor < 6):
        logger.error(f"Python version {major}.{minor} is not supported. Please use Python 3.6 or higher.")
        return False
    
    return True

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        "flask",
        "flask-sqlalchemy",
        "sqlalchemy",
        "psycopg2-binary",
        "requests",
        "apscheduler"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Installing missing packages...")
        
        for package in missing_packages:
            success, output = run_command(f"{sys.executable} -m pip install {package}")
            if success:
                logger.info(f"Successfully installed {package}")
            else:
                logger.error(f"Failed to install {package}: {output}")
                return False
    
    return True

def run_cleanup():
    """Run the cleanup script"""
    logger.info("Running cleanup script...")
    
    if os.path.exists("cleanup.py"):
        success, output = run_command(f"{sys.executable} cleanup.py")
        if success:
            logger.info("Cleanup completed successfully")
            return True
        else:
            logger.error(f"Cleanup failed: {output}")
            return False
    else:
        logger.error("Cleanup script not found")
        return False

def apply_optimizations():
    """Apply all optimizations"""
    logger.info("Applying performance optimizations...")
    
    if os.path.exists("performance_optimizer.py"):
        success, output = run_command(f"{sys.executable} performance_optimizer.py")
        if success:
            logger.info("Performance optimizations applied successfully")
            return True
        else:
            logger.error(f"Performance optimizations failed: {output}")
            return False
    else:
        logger.error("Performance optimizer script not found")
        return False

def create_startup_script():
    """Create an optimized startup script"""
    logger.info("Creating optimized startup script...")
    
    startup_script = """#!/usr/bin/env python
\"\"\"
Optimized startup script for Housing Maintenance application.
This script starts the application with optimized settings.
\"\"\"
import os
import sys
import logging
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set environment variables for better performance
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONOPTIMIZE"] = "2"

if __name__ == "__main__":
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    
    logger.info(f"Starting Housing Maintenance application on port {port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
"""
    
    try:
        with open("start.py", "w") as f:
            f.write(startup_script)
        
        # Make the script executable on Unix-like systems
        if os.name != "nt":
            os.chmod("start.py", 0o755)
        
        logger.info("Created optimized startup script: start.py")
        return True
    except Exception as e:
        logger.error(f"Failed to create startup script: {str(e)}")
        return False

def run_installation():
    """Run the complete installation process"""
    print("=" * 80)
    print("INSTALLING HOUSING MAINTENANCE OPTIMIZATIONS")
    print("=" * 80)
    
    # Step 1: Check Python version
    print("\n1. Checking Python version...")
    if not check_python_version():
        print("ERROR: Python version check failed. Please use Python 3.6 or higher.")
        return False
    
    # Step 2: Check dependencies
    print("\n2. Checking dependencies...")
    if not check_dependencies():
        print("ERROR: Dependency check failed. Please install required packages manually.")
        return False
    
    # Step 3: Run cleanup
    print("\n3. Running cleanup...")
    if not run_cleanup():
        print("WARNING: Cleanup failed. Continuing with installation...")
    
    # Step 4: Apply optimizations
    print("\n4. Applying optimizations...")
    if not apply_optimizations():
        print("ERROR: Failed to apply optimizations.")
        return False
    
    # Step 5: Create startup script
    print("\n5. Creating startup script...")
    if not create_startup_script():
        print("WARNING: Failed to create startup script. You can still run the application using 'python app.py'.")
    
    print("\n" + "=" * 80)
    print("INSTALLATION COMPLETE")
    print("=" * 80)
    print("\nThe Housing Maintenance application has been optimized successfully.")
    print("You can now start the application using:")
    print("  python start.py [port]")
    
    return True

if __name__ == "__main__":
    run_installation()
