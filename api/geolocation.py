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

# Import config directly
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
import config

logger = logging.getLogger(__name__)

class GeolocationService:
    """
    Service for handling location-based functionalities.
    """
    
    def __init__(self):
        """Initialize the geolocation service."""
        self.api_url = "https://nominatim.openstreetmap.org/search"
        self.default_location = {"lat": 42.4072, "lon": -71.3824}  # Massachusetts
        self.recycling_centers_radius = 30  # km - increased from 10 to 30 for wider coverage
        
        logger.info("GeolocationService initialized")
    
    def get_location_from_address(self, address):
        """
        Convert an address to coordinates.
        
        Args:
            address (str): The address to geocode
            
        Returns:
            tuple: (latitude, longitude) or None if not found
        """
        if not address or address.strip() == "":
            logger.warning("Empty address provided to geocoder")
            return None
            
        try:
            # Try to normalize the address - strip extra spaces, add country if not specified
            normalized_address = address.strip()
            
            # For Massachusetts towns and cities, add MA if not present
            ma_cities = ["andover", "lawrence", "haverhill", "lowell", "methuen", "north reading", "reading", "sudbury"]
            address_lower = normalized_address.lower()
            
            # Check if this is a Massachusetts city without state specification
            if any(city in address_lower for city in ma_cities) and "ma" not in address_lower and "massachusetts" not in address_lower:
                if "," in normalized_address:
                    normalized_address += ", MA, USA"
                else:
                    normalized_address += ", MA, USA"
            elif "USA" not in normalized_address.upper() and "US" not in normalized_address.upper():
                if "," in normalized_address:
                    normalized_address += ", USA"
                else:
                    normalized_address += ", USA"
            
            logger.info(f"Geocoding address: {normalized_address} (original: {address})")
            
            # First attempt with OpenStreetMap Nominatim
            coords = self._try_nominatim_geocoding(normalized_address)
            if coords:
                logger.info(f"Successfully geocoded address: {normalized_address} -> {coords}")
                return coords
                
            # If first attempt failed and it might be a zip code, try a zip code specific format
            if normalized_address.replace(", USA", "").strip().isdigit() or \
               (len(normalized_address) >= 5 and normalized_address[:5].isdigit()):
                zip_code = normalized_address.split(",")[0].strip()
                logger.info(f"Trying zip code specific format: {zip_code}")
                coords = self._try_nominatim_geocoding(f"zipcode {zip_code}, USA")
                if coords:
                    logger.info(f"Successfully geocoded zip code: {zip_code} -> {coords}")
                    return coords
            
            # Last attempt: If it looks like a Massachusetts town, try adding Massachusetts explicitly
            if any(city in address_lower for city in ma_cities) and "massachusetts" not in address_lower:
                explicit_address = normalized_address.replace("MA,", "Massachusetts,").replace("ma,", "Massachusetts,")
                if "Massachusetts" not in explicit_address:
                    explicit_address = normalized_address + ", Massachusetts, USA"
                
                logger.info(f"Trying explicit Massachusetts format: {explicit_address}")
                coords = self._try_nominatim_geocoding(explicit_address)
                if coords:
                    logger.info(f"Successfully geocoded with explicit Massachusetts format: {explicit_address} -> {coords}")
                    return coords
            
            # If all attempts failed, return default Massachusetts location
            logger.warning(f"Could not get coordinates for address: {address}. Using default location.")
            return (self.default_location['lat'], self.default_location['lon'])
            
        except Exception as e:
            logger.error(f"Error geocoding address: {e}", exc_info=True)
            # Return default location instead of None to prevent map failures
            return (self.default_location['lat'], self.default_location['lon'])
            
    def _try_nominatim_geocoding(self, address):
        """
        Helper method to try geocoding with Nominatim.
        
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
            
            # Add a delay to respect Nominatim's usage policy
            import time
            time.sleep(1)
            
            response = requests.get(self.api_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return (float(data[0]['lat']), float(data[0]['lon']))
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded for geocoding service")
            else:
                logger.warning(f"Geocoding service returned status code: {response.status_code}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error in Nominatim geocoding: {e}", exc_info=True)
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
    
    def find_recycling_centers(self, lat, lon, waste_type=None, radius=None):
        """
        Find recycling centers near a location.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            waste_type (str, optional): Type of waste to recycle
            radius (float, optional): Search radius in kilometers
            
        Returns:
            list: List of nearby recycling centers
        """
        try:
            if radius is None:
                radius = self.recycling_centers_radius
                
            # Real recycling centers across New England
            # Data sourced from public recycling center information
            real_centers = {
                'MA': [
                    {
                        "name": "Andover Recycling Center",
                        "address": "11 Campanelli Dr, Andover, MA 01810",
                        "phone": "(978) 623-8729",
                        "website": "https://andoverma.gov/219/Recycling-Center",
                        "lat": 42.6518,
                        "lon": -71.1431,
                        "accepts": ["cardboard", "paper", "plastic", "metal", "glass", "electronics"]
                    },
                    {
                        "name": "Lawrence Recycling Facility",
                        "address": "1 Auburn St, Lawrence, MA 01841",
                        "phone": "(978) 620-3000",
                        "website": "https://www.cityoflawrence.com/321/Recycling",
                        "lat": 42.7153,
                        "lon": -71.1634,
                        "accepts": ["plastic", "paper", "glass", "metal", "cardboard"]
                    },
                    {
                        "name": "Haverhill Transfer Station",
                        "address": "500 Primrose St, Haverhill, MA 01830",
                        "phone": "(978) 373-8487",
                        "website": "https://www.cityofhaverhill.com/departments/public_works/solid_waste_and_recycling.php",
                        "lat": 42.7749,
                        "lon": -71.0550,
                        "accepts": ["cardboard", "paper", "metal", "glass", "yard waste", "electronics"]
                    },
                    {
                        "name": "Lowell Regional Waste & Recycling",
                        "address": "1 Armory St, Lowell, MA 01850",
                        "phone": "(978) 674-4309",
                        "website": "https://www.lowellma.gov/390/Recycling-Trash",
                        "lat": 42.6389,
                        "lon": -71.3221,
                        "accepts": ["plastic", "paper", "glass", "metal", "electronics", "hazardous"]
                    },
                    {
                        "name": "Methuen Recycling Center",
                        "address": "15 Lindberg Ave, Methuen, MA 01844",
                        "phone": "(978) 983-8545",
                        "website": "https://www.cityofmethuen.net/recycling-enforcement",
                        "lat": 42.7289,
                        "lon": -71.1912,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "yard waste"]
                    },
                    {
                        "name": "North Reading Recycling Center",
                        "address": "40 Winter St, North Reading, MA 01864",
                        "phone": "(978) 664-6043",
                        "website": "https://www.northreadingma.gov/trash-recycling",
                        "lat": 42.5834,
                        "lon": -71.0728,
                        "accepts": ["paper", "plastic", "glass", "metal", "yard waste"]
                    },
                    {
                        "name": "Reading Recycling Center",
                        "address": "75 New Crossing Rd, Reading, MA 01867",
                        "phone": "(781) 942-9077",
                        "website": "https://www.readingma.gov/public-works-department/pages/recycling-information",
                        "lat": 42.5197,
                        "lon": -71.0950,
                        "accepts": ["cardboard", "paper", "plastic", "electronics", "hazardous", "yard waste"]
                    },
                    {
                        "name": "Boston Zero Waste Recycling Center",
                        "address": "815 Albany St, Boston, MA 02119",
                        "phone": "(617) 635-4500",
                        "website": "https://www.boston.gov/departments/public-works/recycling-boston",
                        "lat": 42.3345,
                        "lon": -71.0726,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "hazardous"]
                    },
                    {
                        "name": "Sudbury Transfer Station",
                        "address": "20 Boston Post Rd, Sudbury, MA 01776",
                        "phone": "(978) 440-5421",
                        "website": "https://sudbury.ma.us/transfer/",
                        "lat": 42.3563,
                        "lon": -71.4372,
                        "accepts": ["paper", "plastic", "glass", "metal", "yard waste", "electronics"]
                    }
                ],
                'CT': [
                    {
                        "name": "New Haven Transfer Station",
                        "address": "260 Middletown Ave, New Haven, CT 06513",
                        "phone": "(203) 946-7700",
                        "website": "https://www.newhavenct.gov/living/services/public-works/solid-waste-recycling",
                        "lat": 41.3272,
                        "lon": -72.8877,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "Waterbury Recycling Center",
                        "address": "155 Captain Neville Dr, Waterbury, CT 06705",
                        "phone": "(203) 574-6857",
                        "website": "https://www.waterburyct.org/public-works/solid-waste",
                        "lat": 41.5713,
                        "lon": -73.0380,
                        "accepts": ["paper", "cardboard", "plastic", "glass", "metal"]
                    },
                    {
                        "name": "Hartford Transfer Station",
                        "address": "180 Leibert Rd, Hartford, CT 06120",
                        "phone": "(860) 757-9311",
                        "website": "https://www.hartfordct.gov/Government/Departments/Public-Works/Recycling",
                        "lat": 41.7958,
                        "lon": -72.6567,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "yard waste"]
                    },
                    {
                        "name": "Bridgeport Transfer Station",
                        "address": "475 Asylum St, Bridgeport, CT 06610",
                        "phone": "(203) 576-7751",
                        "website": "https://www.bridgeportct.gov/recycling",
                        "lat": 41.1865,
                        "lon": -73.1812,
                        "accepts": ["cardboard", "paper", "plastic", "metal", "electronics"]
                    },
                    {
                        "name": "Stamford Recycling Center",
                        "address": "101 Harborview Ave, Stamford, CT 06902",
                        "phone": "(203) 977-4140",
                        "website": "https://www.stamfordct.gov/recycling-sanitation",
                        "lat": 41.0397,
                        "lon": -73.5393,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "hazardous"]
                    }
                ],
                'NH': [
                    {
                        "name": "Manchester Recycling Center",
                        "address": "500 Dunbarton Rd, Manchester, NH 03102",
                        "phone": "(603) 624-6444",
                        "website": "https://www.manchesternh.gov/Departments/Solid-Waste-Recycling",
                        "lat": 42.9849,
                        "lon": -71.4697,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "yard waste"]
                    },
                    {
                        "name": "Nashua Recycling Center",
                        "address": "840 W Hollis St, Nashua, NH 03062",
                        "phone": "(603) 589-3410",
                        "website": "https://www.nashuanh.gov/190/Solid-Waste-Department",
                        "lat": 42.7550,
                        "lon": -71.5126,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "yard waste"]
                    },
                    {
                        "name": "Salem Transfer Station",
                        "address": "12 Shannon Rd, Salem, NH 03079",
                        "phone": "(603) 890-2164",
                        "website": "https://www.townofsalemnh.org/transfer-station",
                        "lat": 42.7915,
                        "lon": -71.2307,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    }
                ],
                'RI': [
                    {
                        "name": "Providence Recycling Center",
                        "address": "700 Allens Ave, Providence, RI 02905",
                        "phone": "(401) 467-7550",
                        "website": "https://www.providenceri.gov/public-works/waste-disposal/",
                        "lat": 41.8053,
                        "lon": -71.4001,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "Warwick Recycling Facility",
                        "address": "111 Range Rd, Warwick, RI 02886",
                        "phone": "(401) 738-2000",
                        "website": "https://www.warwickri.gov/public-works/recycling",
                        "lat": 41.7258,
                        "lon": -71.4523,
                        "accepts": ["paper", "plastic", "glass", "metal", "yard waste", "electronics"]
                    }
                ]
            }
            
            # Determine which state we're closest to
            state_centers = {
                'MA': (42.4072, -71.3824),  # Massachusetts center
                'CT': (41.6032, -73.0877),  # Connecticut center
                'NH': (43.1939, -71.5724),  # New Hampshire center
                'RI': (41.6772, -71.5101)   # Rhode Island center
            }
            
            # Find closest state
            closest_state = 'MA'  # Default to MA
            closest_dist = float('inf')
            
            for state, center in state_centers.items():
                dist = self.haversine_distance(lat, lon, center[0], center[1])
                if dist < closest_dist:
                    closest_dist = dist
                    closest_state = state
            
            logger.info(f"Determined closest state to coordinates ({lat}, {lon}) is {closest_state}")
            
            # Get centers from closest state and adjacent states
            adjacent_states = {
                'MA': ['CT', 'NH', 'RI'],
                'CT': ['MA', 'RI'],
                'NH': ['MA'],
                'RI': ['MA', 'CT']
            }
            
            # Start with centers from the closest state
            centers_to_check = real_centers.get(closest_state, [])
            
            # Add centers from adjacent states
            for adj_state in adjacent_states.get(closest_state, []):
                centers_to_check.extend(real_centers.get(adj_state, []))
            
            # Calculate distance for each center
            centers = []
            for center in centers_to_check:
                # Calculate distance
                distance = self.haversine_distance(lat, lon, center['lat'], center['lon'])
                
                # Only include centers within the radius
                if distance <= radius:
                    # Add distance to center data
                    center_copy = center.copy()
                    center_copy['distance'] = distance
                    centers.append(center_copy)
            
            # Log how many centers were found
            logger.info(f"Found {len(centers)} recycling centers within {radius} km of coordinates ({lat}, {lon})")
            
            # Filter by waste type if specified
            if waste_type:
                centers = [center for center in centers if waste_type.lower() in [w.lower() for w in center["accepts"]]]
                
            # Sort by distance
            centers.sort(key=lambda x: x["distance"])
            
            return centers
            
        except Exception as e:
            logger.error(f"Error finding recycling centers: {e}", exc_info=True)
            return [] 