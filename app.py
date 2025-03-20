#!/usr/bin/env python3
"""
RecycleRight - Main Application Entry Point

This is the entry point for the RecycleRight application.
It imports the Flask web interface and runs the application.
"""

import os
import logging
from dotenv import load_dotenv
from ui.web_interface import app

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
log_file = os.getenv('LOG_FILE', 'logs/recycleright.log')

# Ensure log directory exists
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting RecycleRight application...")
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
    
    logger.info("RecycleRight application stopped.") 