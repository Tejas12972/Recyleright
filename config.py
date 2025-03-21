"""
Configuration settings for RecycleRight application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Flask settings
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Database settings
DB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_NAME', 'recycleright')

# File upload settings
UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv('UPLOAD_FOLDER', 'uploads'))
# Parse MAX_CONTENT_LENGTH manually to avoid comment in the value
try:
    max_content = os.getenv('MAX_CONTENT_LENGTH', '16777216')
    MAX_CONTENT_LENGTH = int(max_content.split('#')[0].strip())
except (ValueError, AttributeError):
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Default to 16MB

ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg').split(','))

# Model settings
MODEL_PATH = os.getenv('MODEL_PATH', 'models/waste_classifier.tflite')
# Define both possible paths for labels - the code will check both paths
LABELS_PATH = os.getenv('LABELS_PATH', 'models/labels/waste_labels.txt')
LABELS_PATH_ALT = os.path.join('models', 'labels', 'waste_labels.txt')

# Points system
POINTS_PER_SCAN = int(os.getenv('POINTS_PER_SCAN', 5))
POINTS_PER_CORRECT_DISPOSAL = int(os.getenv('POINTS_PER_CORRECT_DISPOSAL', 10))
MAX_DAILY_POINTS = int(os.getenv('MAX_DAILY_POINTS', 100))

# Achievement levels
ACHIEVEMENT_LEVELS = ['Beginner', 'Intermediate', 'Advanced', 'Expert', 'Master']

# API Keys
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
GEOLOCATION_API_KEY = os.getenv('GEOLOCATION_API_KEY', '')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(BASE_DIR, os.getenv('LOG_FILE', 'logs/recycleright.log'))

# Create required directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True) 