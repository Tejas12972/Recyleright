"""
User interface module for RecycleRight application.
"""

import logging
import os
import sys
import cv2
import numpy as np
import time
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class UserInterface:
    """Main user interface class for RecycleRight application."""
    
    def __init__(self, classifier, guidelines, geo_service, points_system, challenges):
        """
        Initialize the user interface.
        
        Args:
            classifier: WasteClassifier instance.
            guidelines: RecyclingGuidelines instance.
            geo_service: GeolocationService instance.
            points_system: PointsSystem instance.
            challenges: ChallengeSystem instance.
        """
        self.classifier = classifier
        self.guidelines = guidelines
        self.geo_service = geo_service
        self.points_system = points_system
        self.challenges = challenges
        
        # User state
        self.current_user = None
        self.current_location = None
        self.recent_scans = []
        
        logger.info("User interface initialized")
    
    def run(self):
        """Run the main UI loop."""
        logger.info("Starting UI loop")
        
        # In a real application, this would be an event loop for a GUI framework
        # For this implementation, we'll simulate the main operations
        
        try:
            # Demo flow: login, scan waste, get guidelines, update challenges
            self._demo_flow()
            
        except Exception as e:
            logger.error(f"Error in UI loop: {e}", exc_info=True)
    
    def _demo_flow(self):
        """Simulate a demo flow of the application for development/testing."""
        # 1. User Login
        self._login_user("demo_user", "password123")
        
        if not self.current_user:
            return
        
        # 2. Get user location
        self._set_user_location((37.7749, -122.4194))  # San Francisco
        
        # 3. Get active challenges
        challenges = self.challenges.assign_challenges_to_user(self.current_user["id"])
        self._display_challenges(challenges)
        
        # 4. Scan waste items (simulated)
        waste_items = [
            {"image_path": os.path.join(config.ASSETS_DIR, "samples/plastic_bottle.jpg"), "type": "plastic_PET"},
            {"image_path": os.path.join(config.ASSETS_DIR, "samples/paper.jpg"), "type": "paper"},
            {"image_path": os.path.join(config.ASSETS_DIR, "samples/glass_jar.jpg"), "type": "glass"}
        ]
        
        for item in waste_items:
            self._scan_waste_item(item["image_path"])
            time.sleep(1)  # Simulate time between scans
        
        # 5. Show user stats and achievements
        self._display_user_stats()
        self._display_achievements()
        
        # 6. Show leaderboard
        self._display_leaderboard()
    
    def _login_user(self, username, password):
        """
        Simulate user login.
        
        Args:
            username (str): Username.
            password (str): Password.
        """
        logger.info(f"Logging in user: {username}")
        
        # In a real app, this would verify password hash
        # For demo purposes, we'll just get the user by username
        
        from data.database import get_db
        db = get_db()
        
        user = db.get_user(username=username)
        
        if not user:
            # Create user if it doesn't exist (for demo purposes)
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            user_id = db.add_user(
                username=username,
                email=f"{username}@example.com",
                password_hash=password_hash
            )
            
            if user_id:
                user = db.get_user(user_id=user_id)
                logger.info(f"Created new user: {username}")
            else:
                logger.error(f"Failed to create user: {username}")
                return
        
        self.current_user = user
        logger.info(f"User logged in: {username}")
    
    def _set_user_location(self, location):
        """
        Set the current user's location.
        
        Args:
            location (tuple): (latitude, longitude) tuple.
        """
        logger.info(f"Setting user location: {location}")
        self.current_location = location
        
        # Update user location in database
        if self.current_user:
            from data.database import get_db
            db = get_db()
            
            db.update_user_location(self.current_user["id"], location)
            
            # Get region code based on location
            region = self.geo_service.get_region_from_location(location[0], location[1])
            logger.info(f"User region determined: {region}")
    
    def _scan_waste_item(self, image_path):
        """
        Process a waste item scan.
        
        Args:
            image_path (str): Path to the image file.
        """
        logger.info(f"Scanning waste item: {image_path}")
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return
            
            # Classify waste
            waste_type, confidence = self.classifier.get_top_prediction(image)
            
            if not waste_type:
                logger.warning("No waste type identified with sufficient confidence")
                self._display_result(None, 0, "Unknown", None)
                return
            
            logger.info(f"Classified as {waste_type} with confidence {confidence:.2f}")
            
            # Save scan to database
            from data.database import get_db
            db = get_db()
            
            scan_id = db.record_scan(
                user_id=self.current_user["id"],
                waste_type=waste_type,
                confidence=confidence,
                image_path=image_path,
                location=self.current_location
            )
            
            # Award points for scan
            points = self.points_system.award_points_for_scan(
                user_id=self.current_user["id"],
                scan_id=scan_id,
                waste_type=waste_type,
                confidence=confidence
            )
            
            # Get recycling guidelines
            region = self.geo_service.get_region_from_location(
                self.current_location[0], self.current_location[1]
            ) if self.current_location else "default"
            
            guidelines = self.guidelines.get_disposal_instructions(waste_type, region)
            
            # Update challenges progress
            self.challenges.update_challenge_progress(
                user_id=self.current_user["id"],
                goal_type="scan_count"
            )
            
            self.challenges.update_challenge_progress(
                user_id=self.current_user["id"],
                goal_type="scan_type",
                waste_type=waste_type
            )
            
            # Check for new achievements
            new_achievements = self.challenges.check_achievements(self.current_user["id"])
            if new_achievements:
                self._display_new_achievements(new_achievements)
            
            # Add to recent scans
            self.recent_scans.append({
                "id": scan_id,
                "waste_type": waste_type,
                "confidence": confidence,
                "guidelines": guidelines,
                "points": points,
                "timestamp": datetime.now()
            })
            
            # Display result
            self._display_result(waste_type, confidence, guidelines["disposal_method"], guidelines["instructions"])
            
            # Find nearby recycling centers
            if self.current_location:
                centers = self.geo_service.find_recycling_centers(
                    db, self.current_location[0], self.current_location[1], waste_type
                )
                if centers:
                    self._display_recycling_centers(centers)
            
        except Exception as e:
            logger.error(f"Error scanning waste item: {e}", exc_info=True)
    
    def _confirm_disposal(self, scan_id, waste_type):
        """
        Confirm that a waste item was properly disposed.
        
        Args:
            scan_id (int): The scan ID.
            waste_type (str): The waste type.
        """
        logger.info(f"Confirming disposal of {waste_type} (scan ID: {scan_id})")
        
        # Award points for correct disposal
        points = self.points_system.award_points_for_correct_disposal(
            user_id=self.current_user["id"],
            waste_type=waste_type
        )
        
        # Update challenges progress
        self.challenges.update_challenge_progress(
            user_id=self.current_user["id"],
            goal_type="recycle_type",
            waste_type=waste_type
        )
        
        logger.info(f"Awarded {points} points for correct disposal")
        
        # Check for new achievements
        new_achievements = self.challenges.check_achievements(self.current_user["id"])
        if new_achievements:
            self._display_new_achievements(new_achievements)
    
    def _display_result(self, waste_type, confidence, disposal_method, instructions):
        """
        Display the waste classification result.
        
        Args:
            waste_type (str): The identified waste type.
            confidence (float): The confidence score.
            disposal_method (str): The recommended disposal method.
            instructions (str): Disposal instructions.
        """
        # In a real app, this would update the UI
        # For this implementation, we'll just log the result
        if waste_type:
            logger.info(f"Result: {waste_type} (Confidence: {confidence:.2f})")
            logger.info(f"Disposal Method: {disposal_method}")
            logger.info(f"Instructions: {instructions}")
        else:
            logger.info("Result: Unknown waste type")
    
    def _display_recycling_centers(self, centers):
        """
        Display nearby recycling centers.
        
        Args:
            centers (list): List of recycling centers.
        """
        # In a real app, this would update the UI
        # For this implementation, we'll just log the centers
        logger.info(f"Found {len(centers)} nearby recycling centers:")
        for i, center in enumerate(centers[:3]):  # Show top 3
            logger.info(f"{i+1}. {center['name']} - {center['address']} ({center['distance']:.1f} km)")
    
    def _display_challenges(self, challenges):
        """
        Display active challenges.
        
        Args:
            challenges (list): List of active challenges.
        """
        # In a real app, this would update the UI
        # For this implementation, we'll just log the challenges
        logger.info(f"Active Challenges ({len(challenges)}):")
        for challenge in challenges:
            logger.info(f"- {challenge['title']}: {challenge['progress']}/{challenge['goal_target']} ({challenge['percentage']}%)")
    
    def _display_user_stats(self):
        """Display user statistics."""
        # Get user stats
        stats = self.points_system.get_user_stats(self.current_user["id"])
        
        if not stats:
            return
        
        # In a real app, this would update the UI
        # For this implementation, we'll just log the stats
        logger.info(f"User Stats - Points: {stats['points']}, Level: {stats['level']}, Rank: {stats['rank']}")
        if stats['next_level']:
            logger.info(f"Next Level: {stats['next_level']} (Needs {stats['points_to_next_level']} more points)")
    
    def _display_achievements(self):
        """Display user achievements."""
        # Get user achievements
        achievements = self.challenges.get_user_achievements(self.current_user["id"])
        
        # In a real app, this would update the UI
        # For this implementation, we'll just log the achievements
        logger.info(f"Earned Achievements ({len(achievements['earned'])}):")
        for achievement in achievements['earned'][:3]:  # Show top 3
            logger.info(f"- {achievement['name']}: {achievement['description']}")
        
        logger.info(f"Upcoming Achievements ({len(achievements['unearned'])}):")
        for achievement in achievements['unearned'][:3]:  # Show top 3
            logger.info(f"- {achievement['name']}: {achievement['progress']}/{achievement['threshold']} ({achievement['percentage']}%)")
    
    def _display_new_achievements(self, achievements):
        """
        Display newly earned achievements.
        
        Args:
            achievements (list): List of new achievements.
        """
        # In a real app, this would show a notification or popup
        # For this implementation, we'll just log the achievements
        logger.info(f"New Achievements Earned ({len(achievements)}):")
        for achievement in achievements:
            logger.info(f"- {achievement['name']}: {achievement['description']} (+{achievement['points_reward']} points)")
    
    def _display_leaderboard(self):
        """Display the leaderboard."""
        # Get leaderboard
        leaderboard = self.points_system.get_leaderboard(limit=5)
        
        # In a real app, this would update the UI
        # For this implementation, we'll just log the leaderboard
        logger.info("Leaderboard:")
        for entry in leaderboard:
            logger.info(f"{entry['rank']}. {entry['username']} - {entry['points']} points ({entry['level']})")

class CameraInterface:
    """Camera interface for capturing waste images."""
    
    def __init__(self):
        """Initialize the camera interface."""
        self.camera = None
        logger.info("Camera interface initialized")
    
    def open_camera(self):
        """Open the camera."""
        try:
            self.camera = cv2.VideoCapture(0)  # 0 is usually the default camera
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
            
            logger.info("Camera opened successfully")
            return True
        except Exception as e:
            logger.error(f"Error opening camera: {e}", exc_info=True)
            return False
    
    def capture_image(self):
        """
        Capture an image from the camera.
        
        Returns:
            numpy.ndarray: The captured image or None if failed.
        """
        if not self.camera or not self.camera.isOpened():
            logger.error("Camera not open")
            return None
        
        try:
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Failed to capture image")
                return None
            
            logger.info("Image captured successfully")
            return frame
        except Exception as e:
            logger.error(f"Error capturing image: {e}", exc_info=True)
            return None
    
    def save_image(self, image, filename):
        """
        Save an image to disk.
        
        Args:
            image (numpy.ndarray): The image to save.
            filename (str): The filename to save to.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            directory = os.path.dirname(filename)
            os.makedirs(directory, exist_ok=True)
            
            result = cv2.imwrite(filename, image)
            if not result:
                logger.error(f"Failed to save image to {filename}")
                return False
            
            logger.info(f"Image saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving image: {e}", exc_info=True)
            return False
    
    def close_camera(self):
        """Close the camera."""
        if self.camera:
            self.camera.release()
            logger.info("Camera closed")
        self.camera = None

class MapInterface:
    """Map interface for displaying recycling centers."""
    
    def __init__(self):
        """Initialize the map interface."""
        logger.info("Map interface initialized")
    
    def show_recycling_centers(self, centers, user_location):
        """
        Display recycling centers on a map.
        
        Args:
            centers (list): List of recycling centers.
            user_location (tuple): (latitude, longitude) tuple of user's location.
        """
        # In a real app, this would display a map with markers
        # For this implementation, we'll just log the centers
        logger.info(f"Showing {len(centers)} recycling centers on map around {user_location}")
        for i, center in enumerate(centers):
            logger.info(f"{i+1}. {center['name']} - {center['distance']:.1f} km away") 