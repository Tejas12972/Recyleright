"""
Database module for RecycleRight application using MongoDB.
"""

import logging
import os
import json
from datetime import datetime
import pymongo
from bson.objectid import ObjectId
import hashlib
import math
import time
from urllib.parse import quote_plus
import random

import config

logger = logging.getLogger(__name__)

# Global database connection
_db_instance = None

def get_db():
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        if not config.DB_URI:
            raise ValueError("MongoDB URI not configured. Please check your .env file.")
        _db_instance = Database(config.DB_URI)
    return _db_instance

class Database:
    """Database class for storing and retrieving application data using MongoDB."""
    
    def __init__(self, uri):
        """
        Initialize the database connection.
        
        Args:
            uri (str): MongoDB connection URI.
        """
        self.uri = uri
        self.client = None
        self.db = None
        self.connected = False
        self.mock_mode = False
        
        # Connect to the database
        self.connect()
    
    def connect(self):
        """Establish a connection to the MongoDB database."""
        try:
            if not self.connected:
                # Configure MongoDB client with appropriate settings for Atlas
                self.client = pymongo.MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                    maxPoolSize=50,
                    retryWrites=True,
                    w='majority'
                )
                
                # Get database instance
                self.db = self.client[config.DB_NAME]
                
                # Test connection
                self.client.server_info()
                self.connected = True
                logger.info(f"Connected to MongoDB database {config.DB_NAME}")
                
                # Set up collections after successful connection
                self.setup_collections()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            self.connected = False
            logger.error(f"Could not connect to MongoDB server: {e}", exc_info=True)
            raise
        except pymongo.errors.OperationFailure as e:
            self.connected = False
            logger.error(f"MongoDB authentication failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.connected = False
            logger.error(f"Error connecting to MongoDB: {e}", exc_info=True)
            raise

    def ensure_connected(self):
        """Ensure database is connected before operations."""
        if not self.connected:
            retries = 3
            while retries > 0:
                try:
                    self.connect()
                    break
                except Exception as e:
                    retries -= 1
                    if retries == 0:
                        logger.error("All connection retries failed.")
                        raise
                    time.sleep(1)  # Wait before retrying
    
    def close(self):
        """Close the database connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def setup_collections(self):
        """Set up collections and indexes if they don't exist."""
        try:
            # Create collections if they don't exist
            collections = ["users", "scans", "recycling_guidelines", "recycling_centers", 
                          "challenges", "user_challenges", "achievements", "user_achievements",
                          "educational_content"]
            
            for collection_name in collections:
                if collection_name not in self.db.list_collection_names():
                    self.db.create_collection(collection_name)
            
            # Create indexes
            self.db.users.create_index([("username", pymongo.ASCENDING)], unique=True)
            self.db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
            
            self.db.scans.create_index([("user_id", pymongo.ASCENDING)])
            self.db.scans.create_index([("timestamp", pymongo.DESCENDING)])
            
            self.db.recycling_guidelines.create_index([
                ("waste_type", pymongo.ASCENDING), 
                ("region", pymongo.ASCENDING)
            ], unique=True)
            
            self.db.recycling_centers.create_index([
                ("location", pymongo.GEOSPHERE)
            ])
            
            self.db.user_challenges.create_index([
                ("user_id", pymongo.ASCENDING),
                ("challenge_id", pymongo.ASCENDING)
            ])
            
            self.db.user_achievements.create_index([
                ("user_id", pymongo.ASCENDING),
                ("achievement_id", pymongo.ASCENDING)
            ], unique=True)
            
            logger.info("MongoDB collections and indexes set up successfully")
        except Exception as e:
            logger.error(f"Error setting up MongoDB collections: {e}", exc_info=True)
            raise

    def add_user(self, username, email, password_hash, location=None, settings=None):
        """
        Add a new user to the database.
        
        Args:
            username (str): Username.
            email (str): Email address.
            password_hash (str): Hashed password.
            location (tuple): (latitude, longitude) tuple.
            settings (dict): User settings dictionary.
            
        Returns:
            str: User ID if successful, None otherwise.
        """
        try:
            self.ensure_connected()
            
            location_doc = None
            if location:
                location_doc = {
                    "type": "Point",
                    "coordinates": [location[1], location[0]]  # MongoDB uses [lng, lat]
                }
            
            user_doc = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "date_joined": datetime.now(),
                "points": 0,
                "level": "Beginner",
                "location": location_doc,
                "settings": settings or {}
            }
            
            result = self.db.users.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            logger.info(f"New user '{username}' added with ID {user_id}")
            return user_id
        except pymongo.errors.DuplicateKeyError:
            logger.error(f"User with username '{username}' or email '{email}' already exists")
            return None
        except Exception as e:
            logger.error(f"Error adding user: {e}", exc_info=True)
            return None
    
    def get_user(self, user_id=None, username=None):
        """
        Get user information.
        
        Args:
            user_id (str): User ID.
            username (str): Username.
            
        Returns:
            dict: User information if found, None otherwise.
        """
        try:
            self.ensure_connected()
            
            if user_id:
                user = self.db.users.find_one({"_id": ObjectId(user_id)})
            elif username:
                user = self.db.users.find_one({"username": username})
            else:
                logger.error("Either user_id or username must be provided")
                return None
            
            if user:
                # Convert ObjectId to string for easier handling
                user["id"] = str(user["_id"])
                del user["_id"]
                
                # Extract lat/lon from location document
                if user.get("location"):
                    user["location_lat"] = user["location"]["coordinates"][1]
                    user["location_lon"] = user["location"]["coordinates"][0]
                
                return user
            return None
        except Exception as e:
            logger.error(f"Error retrieving user: {e}", exc_info=True)
            return None
    
    def update_user_location(self, user_id, location):
        """
        Update a user's location.
        
        Args:
            user_id (str): User ID.
            location (tuple): (latitude, longitude) tuple.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            location_doc = {
                "type": "Point",
                "coordinates": [location[1], location[0]]  # MongoDB uses [lng, lat]
            }
            
            result = self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"location": location_doc}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated location for user {user_id}")
                return True
            else:
                logger.warning(f"No location update needed for user {user_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating user location: {e}", exc_info=True)
            return False
    
    def record_scan(self, user_id, waste_type, confidence, image_path=None, location=None):
        """
        Record a waste scan in the database.
        
        Args:
            user_id (str): User ID.
            waste_type (str): Identified waste type.
            confidence (float): Confidence score of the classification.
            image_path (str): Path to the saved image.
            location (tuple): (latitude, longitude) tuple.
            
        Returns:
            str: Scan ID if successful, None otherwise.
        """
        try:
            location_doc = None
            if location:
                location_doc = {
                    "type": "Point",
                    "coordinates": [location[1], location[0]]  # MongoDB uses [lng, lat]
                }
            
            scan_doc = {
                "user_id": ObjectId(user_id),
                "waste_type": waste_type,
                "confidence": confidence,
                "image_path": image_path,
                "location": location_doc,
                "timestamp": datetime.now(),
                "points_earned": 0
            }
            
            result = self.db.scans.insert_one(scan_doc)
            scan_id = str(result.inserted_id)
            
            logger.info(f"New scan recorded with ID {scan_id}")
            return scan_id
        except Exception as e:
            logger.error(f"Error recording scan: {e}", exc_info=True)
            return None
    
    def get_recycling_guidelines(self, waste_type):
        """
        Get recycling guidelines for a specific waste type.
        
        Args:
            waste_type (str): The type of waste to get guidelines for
            
        Returns:
            dict: Guidelines information or None if not found
        """
        try:
            # Make sure we have a valid waste_type and we're connected to MongoDB
            if not waste_type or not self._check_connection():
                return None
                
            # Normalize waste type
            waste_type = waste_type.lower().strip().replace(' ', '_')
            
            # Query the guidelines collection
            guidelines = self.db.guidelines.find_one({'waste_type': waste_type})
            
            if guidelines:
                # Convert ObjectId to string for JSON serialization
                guidelines['_id'] = str(guidelines['_id'])
                return guidelines
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting recycling guidelines: {e}", exc_info=True)
            return None
    
    def get_nearby_recycling_centers(self, lat, lon, radius_km=10, materials=None):
        """
        Find recycling centers near a given location.
        
        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.
            radius_km (float): Search radius in kilometers.
            materials (list): List of materials to filter by.
            
        Returns:
            list: List of nearby recycling centers.
        """
        try:
            # Convert km to radians (Earth radius is approximately 6371 km)
            radius_radians = radius_km / 6371.0
            
            # Use MongoDB's geospatial query to find nearby centers
            query = {
                "location": {
                    "$geoWithin": {
                        "$centerSphere": [[lon, lat], radius_radians]
                    }
                }
            }
            
            # Add materials filter if specified
            if materials:
                query["accepted_materials"] = {"$in": materials}
            
            centers = list(self.db.recycling_centers.find(query))
            
            # Calculate distance for each center and format result
            result = []
            for center in centers:
                # Calculate distance using Haversine formula
                center_lng = center["location"]["coordinates"][0]
                center_lat = center["location"]["coordinates"][1]
                distance = self._calculate_distance(lat, lon, center_lat, center_lng)
                
                center_dict = {
                    "id": str(center["_id"]),
                    "name": center["name"],
                    "address": center["address"],
                    "location_lat": center_lat,
                    "location_lon": center_lng,
                    "hours": center.get("hours"),
                    "accepted_materials": center.get("accepted_materials", []),
                    "notes": center.get("notes"),
                    "distance": distance
                }
                
                result.append(center_dict)
            
            # Sort by distance
            result.sort(key=lambda x: x["distance"])
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving recycling centers: {e}", exc_info=True)
            return []
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates using the Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates.
            lat2, lon2: Second point coordinates.
            
        Returns:
            float: Distance in kilometers.
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = 6371 * c  # Earth radius in km
        
        return distance

    def insert_recycling_guideline(self, waste_type, region, instructions, recyclable, special_handling=None):
        """
        Insert a recycling guideline into the database.
        
        Args:
            waste_type (str): Type of waste material.
            region (str): Geographic region code.
            instructions (str): Recycling instructions.
            recyclable (bool): Whether the material is recyclable.
            special_handling (str): Special handling instructions.
            
        Returns:
            str: Guideline ID if successful, None otherwise.
        """
        try:
            guideline_doc = {
                "waste_type": waste_type,
                "region": region,
                "instructions": instructions,
                "recyclable": recyclable,
                "special_handling": special_handling
            }
            
            # Use upsert to handle duplicates
            result = self.db.recycling_guidelines.update_one(
                {"waste_type": waste_type, "region": region},
                {"$set": guideline_doc},
                upsert=True
            )
            
            if result.upserted_id:
                guideline_id = str(result.upserted_id)
                logger.info(f"Inserted recycling guideline for {waste_type} in {region}")
            else:
                # Get the ID of the updated document
                guideline = self.db.recycling_guidelines.find_one({
                    "waste_type": waste_type, 
                    "region": region
                })
                guideline_id = str(guideline["_id"])
                logger.info(f"Updated recycling guideline for {waste_type} in {region}")
            
            return guideline_id
        except Exception as e:
            logger.error(f"Error inserting recycling guideline: {e}", exc_info=True)
            return None

    def insert_recycling_center(self, name, address, lat, lon, hours=None, accepted_materials=None, notes=None):
        """
        Insert a recycling center into the database.
        
        Args:
            name (str): Center name.
            address (str): Center address.
            lat (float): Latitude.
            lon (float): Longitude.
            hours (str): Operating hours.
            accepted_materials (list): List of accepted materials.
            notes (str): Additional notes.
            
        Returns:
            str: Center ID if successful, None otherwise.
        """
        try:
            location_doc = {
                "type": "Point",
                "coordinates": [lon, lat]  # MongoDB uses [lng, lat]
            }
            
            center_doc = {
                "name": name,
                "address": address,
                "location": location_doc,
                "hours": hours,
                "accepted_materials": accepted_materials or [],
                "notes": notes
            }
            
            result = self.db.recycling_centers.insert_one(center_doc)
            center_id = str(result.inserted_id)
            
            logger.info(f"Inserted recycling center: {name}")
            return center_id
        except Exception as e:
            logger.error(f"Error inserting recycling center: {e}", exc_info=True)
            return None

    def insert_challenge(self, title, description, goal_type, goal_target, 
                         difficulty, points_reward, duration_days, active=True):
        """
        Insert a challenge into the database.
        
        Args:
            title (str): Challenge title.
            description (str): Challenge description.
            goal_type (str): Type of goal (e.g., 'scan_count').
            goal_target (int): Target value to complete the challenge.
            difficulty (str): Challenge difficulty.
            points_reward (int): Points awarded for completion.
            duration_days (int): Duration in days.
            active (bool): Whether the challenge is active.
            
        Returns:
            str: Challenge ID if successful, None otherwise.
        """
        try:
            challenge_doc = {
                "title": title,
                "description": description,
                "goal_type": goal_type,
                "goal_target": goal_target,
                "difficulty": difficulty,
                "points_reward": points_reward,
                "duration_days": duration_days,
                "active": active
            }
            
            result = self.db.challenges.insert_one(challenge_doc)
            challenge_id = str(result.inserted_id)
            
            logger.info(f"Inserted challenge: {title}")
            return challenge_id
        except Exception as e:
            logger.error(f"Error inserting challenge: {e}", exc_info=True)
            return None

    def assign_challenge_to_user(self, user_id, challenge_id, duration_days):
        """
        Assign a challenge to a user.
        
        Args:
            user_id (str): User ID.
            challenge_id (str): Challenge ID.
            duration_days (int): Duration in days.
            
        Returns:
            str: User challenge ID if successful, None otherwise.
        """
        try:
            start_date = datetime.now()
            end_date = start_date + datetime.timedelta(days=duration_days)
            
            user_challenge_doc = {
                "user_id": ObjectId(user_id),
                "challenge_id": ObjectId(challenge_id),
                "start_date": start_date,
                "end_date": end_date,
                "progress": 0,
                "completed": False,
                "reward_claimed": False
            }
            
            result = self.db.user_challenges.insert_one(user_challenge_doc)
            user_challenge_id = str(result.inserted_id)
            
            logger.info(f"Assigned challenge {challenge_id} to user {user_id}")
            return user_challenge_id
        except Exception as e:
            logger.error(f"Error assigning challenge to user: {e}", exc_info=True)
            return None

    def get_user_active_challenges(self, user_id):
        """
        Get active challenges for a user.
        
        Args:
            user_id (str): User ID.
            
        Returns:
            list: Active challenges.
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "user_id": ObjectId(user_id),
                        "completed": False,
                        "end_date": {"$gt": datetime.now()}
                    }
                },
                {
                    "$lookup": {
                        "from": "challenges",
                        "localField": "challenge_id",
                        "foreignField": "_id",
                        "as": "challenge"
                    }
                },
                {"$unwind": "$challenge"},
                {
                    "$project": {
                        "_id": 1,
                        "user_id": 1,
                        "challenge_id": 1,
                        "start_date": 1,
                        "end_date": 1,
                        "progress": 1,
                        "completed": 1,
                        "reward_claimed": 1,
                        "title": "$challenge.title",
                        "description": "$challenge.description",
                        "goal_type": "$challenge.goal_type",
                        "goal_target": "$challenge.goal_target",
                        "difficulty": "$challenge.difficulty",
                        "points_reward": "$challenge.points_reward",
                        "duration_days": "$challenge.duration_days"
                    }
                },
                {"$sort": {"end_date": 1}}
            ]
            
            challenges = list(self.db.user_challenges.aggregate(pipeline))
            
            # Format results
            result = []
            for challenge in challenges:
                challenge["id"] = str(challenge["_id"])
                challenge["user_id"] = str(challenge["user_id"])
                challenge["challenge_id"] = str(challenge["challenge_id"])
                challenge["percentage"] = min(100, int((challenge["progress"] / challenge["goal_target"]) * 100))
                del challenge["_id"]
                result.append(challenge)
            
            return result
        except Exception as e:
            logger.error(f"Error getting user active challenges: {e}", exc_info=True)
            return []

    def update_challenge_progress(self, user_challenge_id, progress):
        """
        Update progress for a user challenge.
        
        Args:
            user_challenge_id (str): User challenge ID.
            progress (int): New progress value.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Get current challenge
            challenge = self.db.user_challenges.find_one({"_id": ObjectId(user_challenge_id)})
            if not challenge:
                logger.error(f"Challenge {user_challenge_id} not found")
                return False
            
            # Update progress
            completed = progress >= challenge.get("goal_target", 0)
            
            result = self.db.user_challenges.update_one(
                {"_id": ObjectId(user_challenge_id)},
                {
                    "$set": {
                        "progress": progress,
                        "completed": completed
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated progress for challenge {user_challenge_id} to {progress}")
                return True
            else:
                logger.warning(f"No update needed for challenge {user_challenge_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating challenge progress: {e}", exc_info=True)
            return False

    def update_user_points(self, user_id, points_to_add):
        """
        Add points to a user's account and update level if necessary.
        
        Args:
            user_id (str): User ID.
            points_to_add (int): Points to add.
            
        Returns:
            dict: Updated user data or None if failed.
        """
        try:
            # Get current user data
            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            current_points = user.get("points", 0)
            current_level = user.get("level", "Beginner")
            
            # Add points
            new_points = current_points + points_to_add
            
            # Check if user has leveled up
            new_level = self._calculate_level(new_points)
            
            # Update user record
            result = self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"points": new_points, "level": new_level}}
            )
            
            if result.modified_count > 0:
                if new_level != current_level:
                    logger.info(f"User {user_id} leveled up from {current_level} to {new_level}")
                else:
                    logger.info(f"Added {points_to_add} points to user {user_id}, now at {new_points}")
                
                return {"points": new_points, "level": new_level}
            else:
                logger.warning(f"No update needed for user {user_id}")
                return None
        except Exception as e:
            logger.error(f"Error updating user points: {e}", exc_info=True)
            return None

    def _calculate_level(self, points):
        """
        Calculate the user's level based on total points.
        
        Args:
            points (int): The user's total points.
            
        Returns:
            str: The user's level.
        """
        level_thresholds = {
            "Beginner": 0,
            "Intermediate": 100,
            "Advanced": 500,
            "Expert": 1000,
            "Master": 5000
        }
        
        achievement_levels = config.ACHIEVEMENT_LEVELS
        current_level = achievement_levels[0]
        
        for level in achievement_levels:
            if points >= level_thresholds.get(level, 0):
                current_level = level
        
        return current_level

    def get_user_stats(self, user_id):
        """
        Get stats for a user including points, level, and rank.
        
        Args:
            user_id (str): User ID.
            
        Returns:
            dict: User stats.
        """
        try:
            # Get user info
            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # Get user rank
            rank_cursor = self.db.users.count_documents({"points": {"$gt": user["points"]}})
            rank = rank_cursor + 1
            
            # Get next level threshold
            level_thresholds = {
                "Beginner": 0,
                "Intermediate": 100,
                "Advanced": 500,
                "Expert": 1000,
                "Master": 5000
            }
            
            achievement_levels = config.ACHIEVEMENT_LEVELS
            user_level = user["level"]
            level_index = achievement_levels.index(user_level)
            
            next_level = None
            next_level_threshold = None
            points_to_next_level = None
            
            if level_index < len(achievement_levels) - 1:
                next_level = achievement_levels[level_index + 1]
                next_level_threshold = level_thresholds[next_level]
                points_to_next_level = next_level_threshold - user["points"]
            
            return {
                "user_id": str(user["_id"]),
                "points": user["points"],
                "level": user["level"],
                "rank": rank,
                "next_level": next_level,
                "points_to_next_level": points_to_next_level
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}", exc_info=True)
            return None

    def get_leaderboard(self, limit=10):
        """
        Get the user leaderboard based on points.
        
        Args:
            limit (int): Maximum number of users to return.
            
        Returns:
            list: List of user data for the leaderboard.
        """
        try:
            self.ensure_connected()
            
            # Get users sorted by points
            leaders = list(self.db.users.find(
                {},
                {"username": 1, "points": 1, "level": 1, "_id": 0}
            ).sort("points", pymongo.DESCENDING).limit(limit))
            
            return leaders
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}", exc_info=True)
            return []

    def get_object_id(self, id_str):
        """
        Convert string ID to MongoDB ObjectId.
        
        Args:
            id_str (str): String ID.
            
        Returns:
            ObjectId: MongoDB ObjectId instance.
        """
        try:
            return ObjectId(id_str)
        except Exception as e:
            logger.error(f"Error converting string ID to ObjectId: {e}", exc_info=True)
            return None

    def get_user_rank(self, user_id):
        """
        Get the rank of a user on the leaderboard.
        
        Args:
            user_id: The user ID
            
        Returns:
            dict: {rank: int, points: int, total_users: int}
        """
        try:
            # Make sure we have a valid user_id and we're connected to MongoDB
            if not user_id or not self._check_connection():
                return {'rank': 0, 'points': 0, 'total_users': 0}
            
            # Convert user_id to ObjectId if necessary
            user_obj_id = self._get_object_id(user_id)
            
            # Get all users sorted by points
            pipeline = [
                {'$project': {'username': 1, 'points': 1}},
                {'$sort': {'points': -1}}
            ]
            
            users = list(self.db.users.aggregate(pipeline))
            total_users = len(users)
            
            # Find the user's position
            current_user = None
            for i, user in enumerate(users):
                if str(user['_id']) == str(user_obj_id):
                    current_user = user
                    rank = i + 1
                    break
            
            if not current_user:
                return {'rank': 0, 'points': 0, 'total_users': total_users}
                
            return {
                'rank': rank,
                'points': current_user.get('points', 0),
                'total_users': total_users
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user rank: {e}", exc_info=True)
            return {'rank': 0, 'points': 0, 'total_users': 0} 