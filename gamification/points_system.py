"""
Points system module for RecycleRight gamification.
"""

import logging
import datetime
import os

# Add parent directory to path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class PointsSystem:
    """Class for managing user points and levels in the gamification system."""
    
    def __init__(self, db):
        """
        Initialize the points system.
        
        Args:
            db: Database instance.
        """
        self.db = db
        self.points_per_scan = config.POINTS_PER_SCAN
        self.points_per_correct_disposal = config.POINTS_PER_CORRECT_DISPOSAL
        self.max_daily_points = config.MAX_DAILY_POINTS
        self.achievement_levels = config.ACHIEVEMENT_LEVELS
        
        # Points thresholds for each level
        self.level_thresholds = {
            "Beginner": 0,
            "Intermediate": 100,
            "Advanced": 500,
            "Expert": 1000,
            "Master": 5000
        }
    
    def award_points_for_scan(self, user_id, scan_id=None, waste_type=None, confidence=None):
        """
        Award points to a user for scanning an item.
        
        Args:
            user_id (int): The user ID.
            scan_id (int): The scan ID if already recorded.
            waste_type (str): The waste type identified.
            confidence (float): The confidence score of the classification.
            
        Returns:
            int: Points awarded or 0 if failed.
        """
        try:
            # Check if user has reached daily limit
            daily_points = self._get_daily_points(user_id)
            if daily_points >= self.max_daily_points:
                logger.info(f"User {user_id} has reached daily points limit")
                return 0
            
            # Base points for scanning
            points = self.points_per_scan
            
            # Bonus points based on confidence if available
            if confidence and confidence > 0.9:
                points += 2  # Bonus for high confidence
            
            # Ensure we don't exceed daily limit
            remaining_daily_points = self.max_daily_points - daily_points
            if points > remaining_daily_points:
                points = remaining_daily_points
            
            # Update points in the database
            self._add_points_to_user(user_id, points)
            
            # If scan_id is provided, update the scan record
            if scan_id:
                self.db.cursor.execute(
                    "UPDATE scans SET points_earned = ? WHERE id = ?",
                    (points, scan_id)
                )
                self.db.conn.commit()
            
            logger.info(f"Awarded {points} points to user {user_id} for scanning waste")
            return points
            
        except Exception as e:
            logger.error(f"Error awarding points for scan: {e}", exc_info=True)
            return 0
    
    def award_points_for_correct_disposal(self, user_id, waste_type):
        """
        Award points to a user for correctly disposing an item.
        
        Args:
            user_id (int): The user ID.
            waste_type (str): The waste type correctly disposed.
            
        Returns:
            int: Points awarded or 0 if failed.
        """
        try:
            # Check if user has reached daily limit
            daily_points = self._get_daily_points(user_id)
            if daily_points >= self.max_daily_points:
                logger.info(f"User {user_id} has reached daily points limit")
                return 0
            
            # Base points for correct disposal
            points = self.points_per_correct_disposal
            
            # Bonus points for certain waste types that are harder to recycle properly
            if waste_type in ["e_waste", "hazardous", "plastic_PVC", "plastic_PS"]:
                points += 5  # Bonus for difficult materials
            
            # Ensure we don't exceed daily limit
            remaining_daily_points = self.max_daily_points - daily_points
            if points > remaining_daily_points:
                points = remaining_daily_points
            
            # Update points in the database
            self._add_points_to_user(user_id, points)
            
            logger.info(f"Awarded {points} points to user {user_id} for correct disposal of {waste_type}")
            return points
            
        except Exception as e:
            logger.error(f"Error awarding points for correct disposal: {e}", exc_info=True)
            return 0
    
    def award_points_for_challenge(self, user_id, points):
        """
        Award points to a user for completing a challenge.
        
        Args:
            user_id (int): The user ID.
            points (int): The number of points to award.
            
        Returns:
            int: Points awarded or 0 if failed.
        """
        try:
            # For challenge completions, we don't apply the daily limit
            # This is to encourage users to complete challenges
            
            # Update points in the database
            self._add_points_to_user(user_id, points)
            
            logger.info(f"Awarded {points} points to user {user_id} for challenge completion")
            return points
            
        except Exception as e:
            logger.error(f"Error awarding points for challenge: {e}", exc_info=True)
            return 0
    
    def _add_points_to_user(self, user_id, points):
        """
        Add points to a user's account and update level if necessary.
        
        Args:
            user_id (int): The user ID.
            points (int): The number of points to add.
        """
        try:
            # Get current user data
            self.db.cursor.execute(
                "SELECT points, level FROM users WHERE id = ?",
                (user_id,)
            )
            result = self.db.cursor.fetchone()
            
            if not result:
                logger.error(f"User {user_id} not found")
                return
            
            current_points = result["points"]
            current_level = result["level"]
            
            # Add points
            new_points = current_points + points
            
            # Check if user has leveled up
            new_level = self._calculate_level(new_points)
            level_up = new_level != current_level
            
            # Update user record
            self.db.cursor.execute(
                "UPDATE users SET points = ?, level = ? WHERE id = ?",
                (new_points, new_level, user_id)
            )
            self.db.conn.commit()
            
            if level_up:
                logger.info(f"User {user_id} leveled up from {current_level} to {new_level}")
                
        except Exception as e:
            logger.error(f"Error adding points to user: {e}", exc_info=True)
            self.db.conn.rollback()
    
    def _calculate_level(self, points):
        """
        Calculate the user's level based on total points.
        
        Args:
            points (int): The user's total points.
            
        Returns:
            str: The user's level.
        """
        current_level = self.achievement_levels[0]
        
        for level in self.achievement_levels:
            if points >= self.level_thresholds.get(level, 0):
                current_level = level
        
        return current_level
    
    def _get_daily_points(self, user_id):
        """
        Get the total points earned by a user today.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            int: Total points earned today.
        """
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            self.db.cursor.execute("""
            SELECT SUM(points_earned) as total 
            FROM scans 
            WHERE user_id = ? AND date(timestamp) = ?
            """, (user_id, today))
            
            result = self.db.cursor.fetchone()
            
            if result and result["total"]:
                return result["total"]
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting daily points: {e}", exc_info=True)
            return 0
    
    def get_user_stats(self, user_id):
        """
        Get stats for a user including points, level, and rank.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            dict: User stats.
        """
        try:
            # Get user info
            self.db.cursor.execute(
                "SELECT points, level FROM users WHERE id = ?",
                (user_id,)
            )
            user = self.db.cursor.fetchone()
            
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # Get user rank
            self.db.cursor.execute("""
            SELECT COUNT(*) + 1 as rank
            FROM users
            WHERE points > (SELECT points FROM users WHERE id = ?)
            """, (user_id,))
            
            rank_result = self.db.cursor.fetchone()
            rank = rank_result["rank"] if rank_result else None
            
            # Get next level threshold
            user_level = user["level"]
            next_level_index = self.achievement_levels.index(user_level) + 1
            if next_level_index < len(self.achievement_levels):
                next_level = self.achievement_levels[next_level_index]
                next_level_threshold = self.level_thresholds[next_level]
                points_to_next_level = next_level_threshold - user["points"]
            else:
                next_level = None
                next_level_threshold = None
                points_to_next_level = None
            
            return {
                "user_id": user_id,
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
        Get the top users by points.
        
        Args:
            limit (int): Maximum number of users to return.
            
        Returns:
            list: Top users with their points and levels.
        """
        try:
            self.db.cursor.execute("""
            SELECT id, username, points, level
            FROM users
            ORDER BY points DESC
            LIMIT ?
            """, (limit,))
            
            results = self.db.cursor.fetchall()
            
            leaderboard = []
            for i, user in enumerate(results):
                leaderboard.append({
                    "rank": i + 1,
                    "user_id": user["id"],
                    "username": user["username"],
                    "points": user["points"],
                    "level": user["level"]
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}", exc_info=True)
            return [] 