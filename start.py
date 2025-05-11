#!/usr/bin/env python
"""
Optimized startup script for Housing Maintenance application.
This script starts the application with optimized settings.
"""
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
