"""
Challenges module for RecycleRight gamification.
"""

import logging
import datetime
import random
import os

# Add parent directory to path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class ChallengeSystem:
    """Class for managing challenges and achievements in the gamification system."""
    
    def __init__(self, db, points_system):
        """
        Initialize the challenge system.
        
        Args:
            db: Database instance.
            points_system: PointsSystem instance.
        """
        self.db = db
        self.points_system = points_system
        self.daily_challenge_count = config.DAILY_CHALLENGE_COUNT
        self.weekly_challenge_count = config.WEEKLY_CHALLENGE_COUNT
        
        # Ensure default challenges are loaded
        self._load_default_challenges()
        self._load_default_achievements()
    
    def _load_default_challenges(self):
        """Load default challenges into the database if they don't exist."""
        try:
            # Check if challenges already exist
            self.db.cursor.execute("SELECT COUNT(*) FROM challenges")
            count = self.db.cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Found {count} existing challenges in database")
                return
            
            # Define default challenges
            default_challenges = [
                # Daily challenges
                {
                    "title": "Plastic Pioneer",
                    "description": "Scan and correctly identify 3 plastic items.",
                    "goal_type": "scan_type",
                    "goal_target": 3,
                    "difficulty": "easy",
                    "points_reward": 20,
                    "duration_days": 1,
                    "active": True
                },
                {
                    "title": "Paper Protector",
                    "description": "Recycle 5 paper products.",
                    "goal_type": "recycle_type",
                    "goal_target": 5,
                    "difficulty": "easy",
                    "points_reward": 25,
                    "duration_days": 1,
                    "active": True
                },
                {
                    "title": "Glass Guardian",
                    "description": "Properly recycle 2 glass containers.",
                    "goal_type": "recycle_type",
                    "goal_target": 2,
                    "difficulty": "easy",
                    "points_reward": 15,
                    "duration_days": 1,
                    "active": True
                },
                {
                    "title": "Metal Magician",
                    "description": "Recycle 3 metal items.",
                    "goal_type": "recycle_type",
                    "goal_target": 3,
                    "difficulty": "easy",
                    "points_reward": 20,
                    "duration_days": 1,
                    "active": True
                },
                {
                    "title": "Recycling Spree",
                    "description": "Scan and properly dispose of 10 items in a day.",
                    "goal_type": "scan_count",
                    "goal_target": 10,
                    "difficulty": "medium",
                    "points_reward": 50,
                    "duration_days": 1,
                    "active": True
                },
                
                # Weekly challenges
                {
                    "title": "Waste Warrior",
                    "description": "Scan and properly dispose of 25 items in a week.",
                    "goal_type": "scan_count",
                    "goal_target": 25,
                    "difficulty": "medium",
                    "points_reward": 100,
                    "duration_days": 7,
                    "active": True
                },
                {
                    "title": "E-Waste Expert",
                    "description": "Properly dispose of 3 electronic waste items.",
                    "goal_type": "recycle_type",
                    "goal_target": 3,
                    "difficulty": "hard",
                    "points_reward": 75,
                    "duration_days": 7,
                    "active": True
                },
                {
                    "title": "Plastic Detective",
                    "description": "Correctly identify and dispose of all 6 types of plastic.",
                    "goal_type": "unique_types",
                    "goal_target": 6,
                    "difficulty": "hard",
                    "points_reward": 120,
                    "duration_days": 7,
                    "active": True
                },
                {
                    "title": "Community Champion",
                    "description": "Visit 3 different recycling centers.",
                    "goal_type": "visit_centers",
                    "goal_target": 3,
                    "difficulty": "medium",
                    "points_reward": 80,
                    "duration_days": 7,
                    "active": True
                },
                {
                    "title": "Knowledge Seeker",
                    "description": "Complete all educational modules.",
                    "goal_type": "complete_education",
                    "goal_target": 5,
                    "difficulty": "medium",
                    "points_reward": 90,
                    "duration_days": 7,
                    "active": True
                }
            ]
            
            # Insert challenges into the database
            for challenge in default_challenges:
                self.db.cursor.execute('''
                INSERT INTO challenges 
                (title, description, goal_type, goal_target, difficulty, points_reward, duration_days, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    challenge["title"],
                    challenge["description"],
                    challenge["goal_type"],
                    challenge["goal_target"],
                    challenge["difficulty"],
                    challenge["points_reward"],
                    challenge["duration_days"],
                    challenge["active"]
                ))
            
            self.db.conn.commit()
            logger.info(f"Added {len(default_challenges)} default challenges to database")
        except Exception as e:
            logger.error(f"Error loading default challenges: {e}", exc_info=True)
            self.db.conn.rollback()
    
    def _load_default_achievements(self):
        """Load default achievements into the database if they don't exist."""
        try:
            # Check if achievements already exist
            self.db.cursor.execute("SELECT COUNT(*) FROM achievements")
            count = self.db.cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Found {count} existing achievements in database")
                return
            
            # Define default achievements
            default_achievements = [
                {
                    "name": "First Scan",
                    "description": "Scan your first waste item.",
                    "icon": "first_scan.png",
                    "requirement": "scan_count",
                    "threshold": 1,
                    "points_reward": 10
                },
                {
                    "name": "Recycling Rookie",
                    "description": "Scan 10 waste items.",
                    "icon": "rookie.png",
                    "requirement": "scan_count",
                    "threshold": 10,
                    "points_reward": 25
                },
                {
                    "name": "Recycling Pro",
                    "description": "Scan 50 waste items.",
                    "icon": "pro.png",
                    "requirement": "scan_count",
                    "threshold": 50,
                    "points_reward": 75
                },
                {
                    "name": "Recycling Master",
                    "description": "Scan 100 waste items.",
                    "icon": "master.png",
                    "requirement": "scan_count",
                    "threshold": 100,
                    "points_reward": 150
                },
                {
                    "name": "Plastic Expert",
                    "description": "Correctly identify all types of plastic.",
                    "icon": "plastic.png",
                    "requirement": "unique_plastic",
                    "threshold": 6,
                    "points_reward": 100
                },
                {
                    "name": "Material Specialist",
                    "description": "Recycle items from all material categories.",
                    "icon": "specialist.png",
                    "requirement": "material_categories",
                    "threshold": 5,
                    "points_reward": 100
                },
                {
                    "name": "Challenge Conqueror",
                    "description": "Complete 10 challenges.",
                    "icon": "challenges.png",
                    "requirement": "complete_challenges",
                    "threshold": 10,
                    "points_reward": 150
                },
                {
                    "name": "Daily Streak",
                    "description": "Use the app for 7 consecutive days.",
                    "icon": "streak.png",
                    "requirement": "daily_streak",
                    "threshold": 7,
                    "points_reward": 100
                },
                {
                    "name": "Perfect Sort",
                    "description": "Achieve 100% accuracy in waste sorting for 20 items.",
                    "icon": "perfect.png",
                    "requirement": "perfect_sorts",
                    "threshold": 20,
                    "points_reward": 200
                }
            ]
            
            # Insert achievements into the database
            for achievement in default_achievements:
                self.db.cursor.execute('''
                INSERT INTO achievements 
                (name, description, icon, requirement, threshold, points_reward)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    achievement["name"],
                    achievement["description"],
                    achievement["icon"],
                    achievement["requirement"],
                    achievement["threshold"],
                    achievement["points_reward"]
                ))
            
            self.db.conn.commit()
            logger.info(f"Added {len(default_achievements)} default achievements to database")
        except Exception as e:
            logger.error(f"Error loading default achievements: {e}", exc_info=True)
            self.db.conn.rollback()
    
    def assign_challenges_to_user(self, user_id):
        """
        Assign active challenges to a user.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            list: Assigned challenges.
        """
        try:
            # Check if user already has active challenges
            self.db.cursor.execute("""
            SELECT COUNT(*) FROM user_challenges 
            WHERE user_id = ? AND completed = 0 AND end_date > datetime('now')
            """, (user_id,))
            
            active_count = self.db.cursor.fetchone()[0]
            
            if active_count >= self.daily_challenge_count + self.weekly_challenge_count:
                logger.info(f"User {user_id} already has enough active challenges")
                return []
            
            # Get existing challenge IDs to avoid duplicates
            self.db.cursor.execute("""
            SELECT challenge_id FROM user_challenges 
            WHERE user_id = ? AND end_date > datetime('now')
            """, (user_id,))
            
            existing_challenges = [row["challenge_id"] for row in self.db.cursor.fetchall()]
            
            # Get available daily challenges
            daily_needed = max(0, self.daily_challenge_count - 
                              sum(1 for c in existing_challenges if self._get_challenge_duration(c) == 1))
            
            if daily_needed > 0:
                daily_challenges = self._get_available_challenges(
                    user_id, existing_challenges, duration_days=1, limit=daily_needed
                )
                
                # Assign daily challenges
                for challenge in daily_challenges:
                    self._assign_challenge(user_id, challenge["id"])
            
            # Get available weekly challenges
            weekly_needed = max(0, self.weekly_challenge_count - 
                               sum(1 for c in existing_challenges if self._get_challenge_duration(c) == 7))
            
            if weekly_needed > 0:
                weekly_challenges = self._get_available_challenges(
                    user_id, existing_challenges, duration_days=7, limit=weekly_needed
                )
                
                # Assign weekly challenges
                for challenge in weekly_challenges:
                    self._assign_challenge(user_id, challenge["id"])
            
            # Get all assigned challenges
            assigned_challenges = self._get_user_active_challenges(user_id)
            
            logger.info(f"Assigned challenges to user {user_id}")
            return assigned_challenges
            
        except Exception as e:
            logger.error(f"Error assigning challenges to user: {e}", exc_info=True)
            self.db.conn.rollback()
            return []
    
    def _get_challenge_duration(self, challenge_id):
        """
        Get the duration of a challenge.
        
        Args:
            challenge_id (int): The challenge ID.
            
        Returns:
            int: Challenge duration in days.
        """
        try:
            self.db.cursor.execute(
                "SELECT duration_days FROM challenges WHERE id = ?",
                (challenge_id,)
            )
            result = self.db.cursor.fetchone()
            
            if result:
                return result["duration_days"]
            return 0
        except Exception as e:
            logger.error(f"Error getting challenge duration: {e}", exc_info=True)
            return 0
    
    def _get_available_challenges(self, user_id, existing_challenges, duration_days, limit):
        """
        Get available challenges for a user.
        
        Args:
            user_id (int): The user ID.
            existing_challenges (list): List of challenge IDs already assigned to the user.
            duration_days (int): Duration of challenges to get.
            limit (int): Maximum number of challenges to return.
            
        Returns:
            list: Available challenges.
        """
        try:
            # Get challenges that match the criteria
            placeholders = ','.join(['?' for _ in existing_challenges]) if existing_challenges else '0'
            query = f"""
            SELECT * FROM challenges 
            WHERE duration_days = ? AND active = 1
            AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT ?
            """
            
            params = [duration_days] + existing_challenges + [limit]
            
            self.db.cursor.execute(query, params)
            challenges = self.db.cursor.fetchall()
            
            # Convert to list of dictionaries
            return [dict(challenge) for challenge in challenges]
            
        except Exception as e:
            logger.error(f"Error getting available challenges: {e}", exc_info=True)
            return []
    
    def _assign_challenge(self, user_id, challenge_id):
        """
        Assign a challenge to a user.
        
        Args:
            user_id (int): The user ID.
            challenge_id (int): The challenge ID.
            
        Returns:
            int: User challenge ID if successful, None otherwise.
        """
        try:
            # Get challenge duration
            self.db.cursor.execute(
                "SELECT duration_days FROM challenges WHERE id = ?",
                (challenge_id,)
            )
            challenge = self.db.cursor.fetchone()
            
            if not challenge:
                logger.error(f"Challenge {challenge_id} not found")
                return None
            
            # Calculate end date
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(days=challenge["duration_days"])
            
            # Insert user challenge
            self.db.cursor.execute('''
            INSERT INTO user_challenges 
            (user_id, challenge_id, start_date, end_date, progress, completed, reward_claimed)
            VALUES (?, ?, ?, ?, 0, 0, 0)
            ''', (
                user_id,
                challenge_id,
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                end_date.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            self.db.conn.commit()
            user_challenge_id = self.db.cursor.lastrowid
            
            logger.info(f"Assigned challenge {challenge_id} to user {user_id}")
            return user_challenge_id
            
        except Exception as e:
            logger.error(f"Error assigning challenge to user: {e}", exc_info=True)
            self.db.conn.rollback()
            return None
    
    def _get_user_active_challenges(self, user_id):
        """
        Get active challenges for a user.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            list: Active challenges.
        """
        try:
            self.db.cursor.execute("""
            SELECT uc.id, uc.user_id, uc.challenge_id, uc.start_date, uc.end_date, 
                   uc.progress, uc.completed, uc.reward_claimed,
                   c.title, c.description, c.goal_type, c.goal_target, 
                   c.difficulty, c.points_reward, c.duration_days
            FROM user_challenges uc
            JOIN challenges c ON uc.challenge_id = c.id
            WHERE uc.user_id = ? AND uc.completed = 0 AND uc.end_date > datetime('now')
            ORDER BY uc.end_date ASC
            """, (user_id,))
            
            challenges = self.db.cursor.fetchall()
            
            # Convert to list of dictionaries
            result = []
            for challenge in challenges:
                challenge_dict = dict(challenge)
                # Calculate percentage
                challenge_dict["percentage"] = min(100, int((challenge_dict["progress"] / challenge_dict["goal_target"]) * 100))
                result.append(challenge_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user active challenges: {e}", exc_info=True)
            return []
    
    def update_challenge_progress(self, user_id, goal_type, waste_type=None):
        """
        Update progress for user challenges based on an action.
        
        Args:
            user_id (int): The user ID.
            goal_type (str): The type of action (e.g., 'scan_count', 'recycle_type').
            waste_type (str): The waste type, if applicable.
            
        Returns:
            list: Completed challenges.
        """
        try:
            # Get active challenges that match the goal type
            self.db.cursor.execute("""
            SELECT uc.id, uc.challenge_id, uc.progress, c.goal_target, c.goal_type, c.points_reward
            FROM user_challenges uc
            JOIN challenges c ON uc.challenge_id = c.id
            WHERE uc.user_id = ? AND uc.completed = 0 AND c.goal_type = ?
            """, (user_id, goal_type))
            
            challenges = self.db.cursor.fetchall()
            completed_challenges = []
            
            for challenge in challenges:
                progress_updated = False
                
                # Check specific waste type requirements
                if goal_type == "scan_type" or goal_type == "recycle_type":
                    if waste_type and (waste_type.startswith(challenge["goal_type"].split('_')[1]) or 
                                       challenge["goal_type"].split('_')[1] == "any"):
                        progress_updated = True
                else:
                    # For other goal types like scan_count, always update
                    progress_updated = True
                
                if progress_updated:
                    # Update progress
                    new_progress = challenge["progress"] + 1
                    
                    self.db.cursor.execute(
                        "UPDATE user_challenges SET progress = ? WHERE id = ?",
                        (new_progress, challenge["id"])
                    )
                    
                    # Check if challenge is completed
                    if new_progress >= challenge["goal_target"]:
                        self.db.cursor.execute(
                            "UPDATE user_challenges SET completed = 1 WHERE id = ?",
                            (challenge["id"],)
                        )
                        
                        completed_challenges.append({
                            "id": challenge["id"],
                            "challenge_id": challenge["challenge_id"],
                            "points_reward": challenge["points_reward"]
                        })
            
            self.db.conn.commit()
            
            # Award points for completed challenges
            for challenge in completed_challenges:
                self.points_system.award_points_for_challenge(user_id, challenge["points_reward"])
            
            return completed_challenges
            
        except Exception as e:
            logger.error(f"Error updating challenge progress: {e}", exc_info=True)
            self.db.conn.rollback()
            return []
    
    def get_user_achievements(self, user_id):
        """
        Get achievements for a user.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            dict: User achievements and progress.
        """
        try:
            # Get earned achievements
            self.db.cursor.execute("""
            SELECT ua.id, ua.user_id, ua.achievement_id, ua.date_earned,
                   a.name, a.description, a.icon, a.requirement, a.threshold, a.points_reward
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ?
            """, (user_id,))
            
            earned = self.db.cursor.fetchall()
            earned_achievements = [dict(achievement) for achievement in earned]
            earned_ids = [a["achievement_id"] for a in earned_achievements]
            
            # Get unearned achievements
            self.db.cursor.execute("""
            SELECT id, name, description, icon, requirement, threshold, points_reward
            FROM achievements
            WHERE id NOT IN ({})
            """.format(','.join(['?'] * len(earned_ids)) if earned_ids else '0'), 
            earned_ids if earned_ids else [])
            
            unearned = self.db.cursor.fetchall()
            unearned_achievements = [dict(achievement) for achievement in unearned]
            
            # Get user progress for unearned achievements
            for achievement in unearned_achievements:
                progress = self._get_achievement_progress(user_id, achievement["requirement"], achievement["threshold"])
                achievement["progress"] = progress
                achievement["percentage"] = min(100, int((progress / achievement["threshold"]) * 100))
            
            return {
                "earned": earned_achievements,
                "unearned": unearned_achievements
            }
            
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}", exc_info=True)
            return {"earned": [], "unearned": []}
    
    def _get_achievement_progress(self, user_id, requirement, threshold):
        """
        Get progress for an achievement requirement.
        
        Args:
            user_id (int): The user ID.
            requirement (str): The achievement requirement.
            threshold (int): The achievement threshold.
            
        Returns:
            int: Current progress.
        """
        try:
            if requirement == "scan_count":
                self.db.cursor.execute(
                    "SELECT COUNT(*) as count FROM scans WHERE user_id = ?",
                    (user_id,)
                )
                result = self.db.cursor.fetchone()
                return result["count"] if result else 0
                
            elif requirement == "unique_plastic":
                self.db.cursor.execute("""
                SELECT COUNT(DISTINCT waste_type) as count 
                FROM scans 
                WHERE user_id = ? AND waste_type LIKE 'plastic_%'
                """, (user_id,))
                result = self.db.cursor.fetchone()
                return result["count"] if result else 0
                
            elif requirement == "material_categories":
                categories = ["plastic", "paper", "metal", "glass", "organic"]
                count = 0
                for category in categories:
                    self.db.cursor.execute(f"""
                    SELECT COUNT(*) as count 
                    FROM scans 
                    WHERE user_id = ? AND waste_type LIKE '{category}%'
                    """, (user_id,))
                    result = self.db.cursor.fetchone()
                    if result and result["count"] > 0:
                        count += 1
                return count
                
            elif requirement == "complete_challenges":
                self.db.cursor.execute(
                    "SELECT COUNT(*) as count FROM user_challenges WHERE user_id = ? AND completed = 1",
                    (user_id,)
                )
                result = self.db.cursor.fetchone()
                return result["count"] if result else 0
                
            elif requirement == "daily_streak":
                # This would require tracking daily logins, simplifying for now
                return 0
                
            elif requirement == "perfect_sorts":
                self.db.cursor.execute(
                    "SELECT COUNT(*) as count FROM scans WHERE user_id = ? AND confidence > 0.95",
                    (user_id,)
                )
                result = self.db.cursor.fetchone()
                return result["count"] if result else 0
                
            return 0
            
        except Exception as e:
            logger.error(f"Error getting achievement progress: {e}", exc_info=True)
            return 0
    
    def check_achievements(self, user_id):
        """
        Check and award achievements to a user.
        
        Args:
            user_id (int): The user ID.
            
        Returns:
            list: Newly awarded achievements.
        """
        try:
            # Get all achievements
            self.db.cursor.execute("SELECT * FROM achievements")
            achievements = self.db.cursor.fetchall()
            
            # Get already earned achievements
            self.db.cursor.execute(
                "SELECT achievement_id FROM user_achievements WHERE user_id = ?",
                (user_id,)
            )
            earned_ids = [row["achievement_id"] for row in self.db.cursor.fetchall()]
            
            newly_earned = []
            
            # Check each unearned achievement
            for achievement in achievements:
                if achievement["id"] not in earned_ids:
                    progress = self._get_achievement_progress(
                        user_id, achievement["requirement"], achievement["threshold"]
                    )
                    
                    if progress >= achievement["threshold"]:
                        # Award achievement
                        self.db.cursor.execute('''
                        INSERT INTO user_achievements (user_id, achievement_id)
                        VALUES (?, ?)
                        ''', (user_id, achievement["id"]))
                        
                        # Award points
                        self.points_system.award_points_for_challenge(user_id, achievement["points_reward"])
                        
                        newly_earned.append(dict(achievement))
            
            self.db.conn.commit()
            
            if newly_earned:
                logger.info(f"User {user_id} earned {len(newly_earned)} new achievements")
            
            return newly_earned
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}", exc_info=True)
            self.db.conn.rollback()
            return [] 