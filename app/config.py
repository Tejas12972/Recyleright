"""
Configuration settings for the RecycleRight application.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# MongoDB settings
DB_URI = "mongodb://localhost:27017/"
DB_NAME = "recycleright"

# Model settings
MODEL_PATH = os.path.join(MODELS_DIR, "waste_classifier.tflite")
LABELS_PATH = os.path.join(MODELS_DIR, "labels.txt")

# Image settings
INPUT_SIZE = (224, 224)  # Input size for the model
NORMALIZE_MEAN = [0.485, 0.456, 0.406]  # ImageNet normalization values
NORMALIZE_STD = [0.229, 0.224, 0.225]

# Classifier settings
CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence score for valid classification

# Geolocation settings
DEFAULT_LOCATION = {"lat": 37.7749, "lon": -122.4194}  # Default location (San Francisco)
GEOCODING_API_URL = "https://nominatim.openstreetmap.org/search"
RECYCLING_CENTERS_RADIUS = 10  # km

# User settings
POINTS_PER_SCAN = 5
POINTS_PER_CORRECT_DISPOSAL = 10
MAX_DAILY_POINTS = 100

# Gamification settings
DAILY_CHALLENGE_COUNT = 3
WEEKLY_CHALLENGE_COUNT = 5
ACHIEVEMENT_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert", "Master"] 