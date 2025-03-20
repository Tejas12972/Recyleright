"""
Core application module for RecycleRight.
"""

import logging
import os
import sys

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from models.classifier import WasteClassifier
from data.database import Database
from data.recycling_guidelines import RecyclingGuidelines
from api.geolocation import GeolocationService
from ui.interface import UserInterface
from gamification.points_system import PointsSystem
from gamification.challenges import ChallengeSystem

logger = logging.getLogger(__name__)

class App:
    """Main application class that initializes and coordinates all components."""
    
    def __init__(self):
        """Initialize the RecycleRight application."""
        logger.info("Initializing RecycleRight components...")
        
        # Initialize database
        self.db = Database(config.DB_PATH)
        
        # Initialize waste classifier
        self.classifier = WasteClassifier(
            model_path=config.MODEL_PATH,
            labels_path=config.LABELS_PATH
        )
        
        # Initialize recycling guidelines
        self.guidelines = RecyclingGuidelines(self.db)
        
        # Initialize geolocation service
        self.geo_service = GeolocationService()
        
        # Initialize gamification components
        self.points_system = PointsSystem(self.db)
        self.challenges = ChallengeSystem(self.db, self.points_system)
        
        # Initialize user interface
        self.ui = UserInterface(
            classifier=self.classifier,
            guidelines=self.guidelines,
            geo_service=self.geo_service,
            points_system=self.points_system,
            challenges=self.challenges
        )
        
        logger.info("RecycleRight initialization complete.")
    
    def run(self):
        """Run the main application loop."""
        logger.info("Starting RecycleRight main loop.")
        try:
            self.ui.run()
        except KeyboardInterrupt:
            logger.info("Application terminated by user.")
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources before exiting."""
        logger.info("Cleaning up resources...")
        try:
            self.db.close()
            # Add any other cleanup operations here
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True) 