"""
Geolocation service for RecycleRight application.

This module handles location-based services such as finding nearby recycling centers.
"""

import os
import logging
import requests
import json
import math
from datetime import datetime

# Import config using importlib to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location("config", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app/config.py"))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

logger = logging.getLogger(__name__)

class GeolocationService:
    """
    Service for handling location-based functionalities.
    """
    
    def __init__(self):
        """Initialize the geolocation service."""
        self.api_url = "https://nominatim.openstreetmap.org/search"
        self.default_location = {"lat": 37.7749, "lon": -122.4194}  # San Francisco
        self.recycling_centers_radius = 10  # km
        
        logger.info("GeolocationService initialized")
    
    def get_location_from_address(self, address):
        """
        Convert an address to coordinates.
        
        Args:
            address (str): The address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if not found
        """
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1
            }
            
            headers = {
                'User-Agent': 'RecycleRight/1.0'
            }
            
            response = requests.get(self.api_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return (float(data[0]['lat']), float(data[0]['lon']))
            
            logger.warning(f"Could not get coordinates for address: {address}")
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding address: {e}")
            return None
    
    def get_region_from_location(self, lat, lon):
        """
        Get region code from coordinates.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: Region code (e.g., 'US-CA') or 'default' if not found
        """
        try:
            # This would typically use a reverse geocoding API
            # For simplicity, we're returning 'default'
            return 'default'
            
        except Exception as e:
            logger.error(f"Error getting region from location: {e}")
            return 'default'
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            float: Distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    def find_recycling_centers(self, db, lat, lon, waste_type=None, radius_km=None):
        """
        Find recycling centers near a location.
        
        Args:
            db: Database instance
            lat (float): Latitude
            lon (float): Longitude
            waste_type (str, optional): Type of waste to recycle
            radius_km (float, optional): Search radius in kilometers
            
        Returns:
            list: List of nearby recycling centers
        """
        try:
            if radius_km is None:
                radius_km = self.recycling_centers_radius
            
            # Get centers from database
            centers = db.get_nearby_recycling_centers(lat, lon, radius_km, waste_type)
            
            return centers
            
        except Exception as e:
            logger.error(f"Error finding recycling centers: {e}")
            return [] 