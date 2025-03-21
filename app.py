#!/usr/bin/env python3
"""
RecycleRight - Main Application Entry Point

This is the entry point for the RecycleRight application.
It imports the Flask web interface and runs the application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
import config

# Set up logging
if not os.path.exists(os.path.dirname(config.LOG_FILE)):
    os.makedirs(os.path.dirname(config.LOG_FILE))

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(config.LOG_FILE, maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    # Create Flask application
    app = Flask(__name__,
        static_folder='ui/static',
        template_folder='ui/templates'
    )

    # Load configuration
    app.config.from_object(config)
    
    # Set secret key
    app.secret_key = config.SECRET_KEY

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    # Import and register routes
    from ui.routes import register_routes
    register_routes(app)

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    logger.info("Starting RecycleRight application...")
    # Use port 5001 to avoid conflict with AirPlay
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
    
    logger.info("RecycleRight application stopped.") 