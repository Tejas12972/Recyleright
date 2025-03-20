"""
Geolocation service for RecycleRight application.
"""

import logging
import requests
import json
import os

# Add parent directory to path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class GeolocationService:
    """Service for geolocation and recycling centers discovery."""
    
    def __init__(self):
        """Initialize the geolocation service."""
        self.api_url = config.GEOCODING_API_URL
        self.default_location = config.DEFAULT_LOCATION
        self.recycling_centers_radius = config.RECYCLING_CENTERS_RADIUS
    
    def geocode_address(self, address):
        """
        Convert an address to geographic coordinates.
        
        Args:
            address (str): The address to geocode.
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding failed.
        """
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1
            }
            
            headers = {
                'User-Agent': 'RecycleRight/1.0'  # Required by Nominatim service
            }
            
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            
            results = response.json()
            
            if results and len(results) > 0:
                lat = float(results[0]['lat'])
                lon = float(results[0]['lon'])
                logger.info(f"Geocoded address '{address}' to coordinates ({lat}, {lon})")
                return (lat, lon)
            else:
                logger.warning(f"No geocoding results found for address '{address}'")
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding address '{address}': {e}", exc_info=True)
            return None
    
    def reverse_geocode(self, lat, lon):
        """
        Convert coordinates to an address.
        
        Args:
            lat (float): Latitude.
            lon (float): Longitude.
            
        Returns:
            dict: Address details or None if reverse geocoding failed.
        """
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'RecycleRight/1.0'  # Required by Nominatim service
            }
            
            response = requests.get(f"{self.api_url}/reverse", params=params, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result and 'address' in result:
                logger.info(f"Reverse geocoded coordinates ({lat}, {lon}) to address")
                return result['address']
            else:
                logger.warning(f"No reverse geocoding results found for coordinates ({lat}, {lon})")
                return None
                
        except Exception as e:
            logger.error(f"Error reverse geocoding coordinates ({lat}, {lon}): {e}", exc_info=True)
            return None
    
    def get_region_from_location(self, lat, lon):
        """
        Determine the region code from coordinates.
        
        Args:
            lat (float): Latitude.
            lon (float): Longitude.
            
        Returns:
            str: Region code (e.g., 'urban', 'rural', or specific region code).
        """
        try:
            address = self.reverse_geocode(lat, lon)
            
            if not address:
                return "default"
            
            # Determine if location is urban or rural based on address components
            # This is a simplified approach; a real implementation might use more sophisticated methods
            urban_indicators = ['city', 'town', 'borough', 'suburb']
            
            for indicator in urban_indicators:
                if indicator in address:
                    return "urban"
            
            # If a specific county or state is identified, could return that as a region
            if 'county' in address:
                return f"county_{address['county'].lower().replace(' ', '_')}"
            
            return "rural"
            
        except Exception as e:
            logger.error(f"Error determining region from location: {e}", exc_info=True)
            return "default"
    
    def find_recycling_centers(self, db, lat, lon, waste_type=None):
        """
        Find recycling centers near a location that accept a specific waste type.
        
        Args:
            db: Database instance.
            lat (float): Latitude.
            lon (float): Longitude.
            waste_type (str): Type of waste material to filter by.
            
        Returns:
            list: List of nearby recycling centers.
        """
        try:
            # Determine materials to filter by based on waste type
            materials = None
            if waste_type:
                if waste_type.startswith("plastic_"):
                    materials = ["plastic"]
                elif waste_type.startswith("paper"):
                    materials = ["paper"]
                elif waste_type.startswith("metal_"):
                    materials = ["metal"]
                elif waste_type == "glass":
                    materials = ["glass"]
                elif waste_type.startswith("organic_"):
                    materials = ["organic", "compost"]
                elif waste_type == "e_waste":
                    materials = ["e-waste", "electronics"]
                elif waste_type == "hazardous":
                    materials = ["hazardous"]
            
            # Query database for nearby centers
            centers = db.get_nearby_recycling_centers(
                lat, lon, 
                radius_km=self.recycling_centers_radius,
                materials=materials
            )
            
            logger.info(f"Found {len(centers)} recycling centers near ({lat}, {lon})")
            return centers
            
        except Exception as e:
            logger.error(f"Error finding recycling centers: {e}", exc_info=True)
            return [] 