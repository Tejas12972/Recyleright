#!/usr/bin/env python3
"""
RecycleRight - AI-Powered Waste Sorting Assistant

This is the main entry point for the RecycleRight application.
"""

import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import App

def main():
    """Main function to start the RecycleRight application."""
    logger.info("Starting RecycleRight application...")
    try:
        app = App()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 