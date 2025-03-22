#!/usr/bin/env python3
"""
RecycleRight - Main Application Entry Point

This is the entry point for the RecycleRight application.
It imports the Flask web interface and runs the application.
"""

import os
import logging
import json
import uuid
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
import config

# Import application components
from data.database import get_db
from models.waste_classifier import WasteClassifier
from api.geolocation import GeolocationService
from gamification.points_system import PointsSystem

# Set up logging
if not os.path.exists(os.path.dirname(config.LOG_FILE)):
    os.makedirs(os.path.dirname(config.LOG_FILE))

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
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

    # Copy config values explicitly
    app.config['MODEL_PATH'] = config.MODEL_PATH
    app.config['LABELS_PATH'] = config.LABELS_PATH
    app.config['ALLOWED_EXTENSIONS'] = config.ALLOWED_EXTENSIONS
    app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/recycleright')

    # Configure static files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['STATIC_FOLDER'] = 'ui/static'

    # Add MIME type for SVG
    app.config['MIME_TYPES'] = {
        '.svg': 'image/svg+xml'
    }

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

    # Initialize components
    db = get_db()
    geo_service = GeolocationService()
    classifier = WasteClassifier(
        model_path=app.config.get('MODEL_PATH', 'models/waste_classifier.tflite'),
        labels_path=app.config.get('LABELS_PATH', 'models/labels/waste_labels.txt')
    )
    points_system = PointsSystem(db)

    # Create upload directory if it doesn't exist
    UPLOAD_FOLDER = 'ui/static/uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # Make services available to the routes
    app.config['database'] = db
    app.config['waste_classifier'] = classifier
    app.config['geo_service'] = geo_service
    app.config['points_system'] = points_system
    
    # Add Google Maps API key to app config
    app.config['GOOGLE_MAPS_API_KEY'] = config.GOOGLE_MAPS_API_KEY

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