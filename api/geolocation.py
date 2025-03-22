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
        self.recycling_centers_radius = 100  # km - increased from 30 to 100 for much wider coverage
        
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
            
            # Common address abbreviations to expand
            abbrev_map = {
                'rd': 'road',
                'st': 'street', 
                'ave': 'avenue',
                'blvd': 'boulevard',
                'dr': 'drive',
                'ln': 'lane',
                'ct': 'court',
                'pl': 'place',
                'cir': 'circle',
                'pkwy': 'parkway',
                'hwy': 'highway'
            }
            
            # Expand common abbreviations in address (e.g., "rd" to "road")
            words = normalized_address.split()
            for i, word in enumerate(words):
                word_lower = word.lower().rstrip(',.')
                if word_lower in abbrev_map:
                    words[i] = word.replace(word_lower, abbrev_map[word_lower])
            normalized_address = ' '.join(words)
            
            # For Massachusetts towns and cities, add MA if not present
            ma_cities = ["andover", "lawrence", "haverhill", "lowell", "methuen", "north reading", "reading", "sudbury", 
                         "boston", "cambridge", "worcester", "springfield", "framingham", "marlborough", "somerville"]
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
            
            # Try with just the city and state if address has multiple parts
            if len(normalized_address.split(',')) > 1:
                parts = normalized_address.split(',')
                city_state = ', '.join(parts[1:]).strip()
                if city_state:
                    logger.info(f"Trying with just city and state: {city_state}")
                    coords = self._try_nominatim_geocoding(city_state)
                    if coords:
                        logger.info(f"Successfully geocoded with city/state: {city_state} -> {coords}")
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
                
            # Real recycling centers across the USA
            # Data sourced from public recycling center information
            real_centers = {
                # Massachusetts
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
                        "name": "Boston Zero Waste Recycling Center",
                        "address": "815 Albany St, Boston, MA 02119",
                        "phone": "(617) 635-4500",
                        "website": "https://www.boston.gov/departments/public-works/recycling-boston",
                        "lat": 42.3345,
                        "lon": -71.0726,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "hazardous"]
                    }
                ],
                # Texas
                'TX': [
                    {
                        "name": "Dallas Recycling Center",
                        "address": "4610 S Westmoreland Rd, Dallas, TX 75237",
                        "phone": "(214) 670-4475",
                        "website": "https://dallascityhall.com/departments/sanitation/Pages/recycling.aspx",
                        "lat": 32.6871,
                        "lon": -96.8724,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "McCommas Bluff Recycling Center",
                        "address": "5555 Youngblood Rd, Dallas, TX 75241",
                        "phone": "(214) 670-0977",
                        "website": "https://dallascityhall.com/departments/sanitation/Pages/landfill.aspx",
                        "lat": 32.6667,
                        "lon": -96.7478,
                        "accepts": ["paper", "plastic", "metal", "yard waste", "hazardous", "electronics"]
                    },
                    {
                        "name": "Houston Environmental Service Center - South",
                        "address": "11500 S Post Oak Rd, Houston, TX 77035",
                        "phone": "(713) 837-1310",
                        "website": "https://www.houstontx.gov/solidwaste/recycling.html",
                        "lat": 29.6575,
                        "lon": -95.4758,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "hazardous"]
                    },
                    {
                        "name": "San Antonio Recycling Center",
                        "address": "1800 Wurzbach Pkwy, San Antonio, TX 78216",
                        "phone": "(210) 207-6428",
                        "website": "https://www.sanantonio.gov/swmd/Recycling",
                        "lat": 29.5265,
                        "lon": -98.5137,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "Austin Recycle & Reuse Drop-off Center",
                        "address": "2514 Business Center Dr, Austin, TX 78744",
                        "phone": "(512) 974-4343",
                        "website": "https://www.austintexas.gov/department/recycle-reuse-drop-center",
                        "lat": 30.2058,
                        "lon": -97.7471,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "hazardous", "textiles"]
                    },
                    {
                        "name": "Fort Worth Environmental Collection Center",
                        "address": "6400 Bridge St, Fort Worth, TX 76112",
                        "phone": "(817) 392-1234",
                        "website": "https://www.fortworthtexas.gov/departments/code-compliance/environmental-quality/drop-off",
                        "lat": 32.7666,
                        "lon": -97.2382,
                        "accepts": ["paper", "plastic", "electronics", "hazardous", "chemicals"]
                    }
                ],
                # California
                'CA': [
                    {
                        "name": "San Francisco Recology Recycling Center",
                        "address": "501 Tunnel Ave, San Francisco, CA 94134",
                        "phone": "(415) 330-1400",
                        "website": "https://www.recology.com/recology-san-francisco/",
                        "lat": 37.7128,
                        "lon": -122.3984,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "compost"]
                    },
                    {
                        "name": "LA Recycling Center",
                        "address": "2475 E Olympic Blvd, Los Angeles, CA 90021",
                        "phone": "(323) 901-2605",
                        "website": "https://www.lacitysan.org/san/faces/home",
                        "lat": 34.0313,
                        "lon": -118.2279,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "San Diego Miramar Recycling Center",
                        "address": "5165 Convoy St, San Diego, CA 92111",
                        "phone": "(858) 694-7000",
                        "website": "https://www.sandiego.gov/environmental-services/recycling",
                        "lat": 32.8339,
                        "lon": -117.1541,
                        "accepts": ["paper", "plastic", "glass", "metal", "yard waste", "electronics"]
                    }
                ],
                # Florida
                'FL': [
                    {
                        "name": "Miami-Dade Recycling Center",
                        "address": "8831 NW 58th St, Doral, FL 33178",
                        "phone": "(305) 594-1420",
                        "website": "https://www.miamidade.gov/global/service.page?Mduid_service=ser1467835326826406",
                        "lat": 25.8277,
                        "lon": -80.3349,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "Orlando Recycling Center",
                        "address": "5901 Young Pine Rd, Orlando, FL 32829",
                        "phone": "(407) 246-2314",
                        "website": "https://www.orlando.gov/Trash-Recycling",
                        "lat": 28.5629,
                        "lon": -81.2471,
                        "accepts": ["paper", "plastic", "glass", "metal", "yard waste", "electronics"]
                    }
                ],
                # New York
                'NY': [
                    {
                        "name": "NYC Department of Sanitation Recycling Center",
                        "address": "400 E 59th St, New York, NY 10022",
                        "phone": "(212) 669-7560",
                        "website": "https://www1.nyc.gov/assets/dsny/site/services/recycling",
                        "lat": 40.7588,
                        "lon": -73.9626,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    },
                    {
                        "name": "Brooklyn Recycling Center",
                        "address": "130 Nostrand Ave, Brooklyn, NY 11205",
                        "phone": "(718) 935-1122",
                        "website": "https://www1.nyc.gov/assets/dsny/site/services/recycling",
                        "lat": 40.6953,
                        "lon": -73.9511,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "textiles"]
                    }
                ],
                # Illinois
                'IL': [
                    {
                        "name": "Chicago Recycling Center",
                        "address": "2700 W 34th St, Chicago, IL 60632",
                        "phone": "(312) 744-1614",
                        "website": "https://www.chicago.gov/city/en/depts/streets/supp_info/recycling1.html",
                        "lat": 41.8310,
                        "lon": -87.6874,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    }
                ],
                # Georgia
                'GA': [
                    {
                        "name": "Atlanta Recycling Center",
                        "address": "1540 Jonesboro Rd SE, Atlanta, GA 30315",
                        "phone": "(404) 330-6333",
                        "website": "https://www.atlantaga.gov/government/departments/public-works/recycling-program",
                        "lat": 33.7224,
                        "lon": -84.3807,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
                    }
                ],
                # Washington
                'WA': [
                    {
                        "name": "Seattle Recycling Center",
                        "address": "1350 N 34th St, Seattle, WA 98103",
                        "phone": "(206) 684-3000",
                        "website": "https://www.seattle.gov/utilities/your-services/collection-and-disposal/recycling",
                        "lat": 47.6492,
                        "lon": -122.3512,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics", "yard waste"]
                    }
                ],
                # Continue with more states if needed
                'CT': [
                    {
                        "name": "New Haven Transfer Station",
                        "address": "260 Middletown Ave, New Haven, CT 06513",
                        "phone": "(203) 946-7700",
                        "website": "https://www.newhavenct.gov/living/services/public-works/solid-waste-recycling",
                        "lat": 41.3272,
                        "lon": -72.8877,
                        "accepts": ["paper", "plastic", "glass", "metal", "electronics"]
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
                    }
                ]
            }
            
            # Define major US regions by state
            us_regions = {
                'Northeast': ['MA', 'CT', 'NH', 'RI', 'ME', 'VT', 'NY', 'NJ', 'PA'],
                'South': ['TX', 'FL', 'GA', 'NC', 'SC', 'VA', 'WV', 'KY', 'TN', 'AR', 'LA', 'MS', 'AL'],
                'Midwest': ['IL', 'IN', 'OH', 'MI', 'WI', 'MN', 'IA', 'MO', 'ND', 'SD', 'NE', 'KS'],
                'West': ['CA', 'WA', 'OR', 'NV', 'ID', 'MT', 'WY', 'UT', 'CO', 'AZ', 'NM', 'HI', 'AK']
            }
            
            # State centers for major states
            state_centers = {
                'MA': (42.4072, -71.3824),  # Massachusetts
                'TX': (31.9686, -99.9018),  # Texas
                'CA': (36.7783, -119.4179), # California
                'FL': (27.6648, -81.5158),  # Florida
                'NY': (42.1657, -74.9481),  # New York
                'IL': (40.6331, -89.3985),  # Illinois
                'GA': (32.1656, -82.9001),  # Georgia
                'WA': (47.7511, -120.7401), # Washington
                'CT': (41.6032, -73.0877),  # Connecticut
                'NH': (43.1939, -71.5724),  # New Hampshire
                'RI': (41.6772, -71.5101)   # Rhode Island
                # Add more states as needed
            }
            
            # Get region based on lat/lon
            # Default to Northeast, but try to determine the correct region
            user_region = 'Northeast'
            closest_state = None
            closest_dist = float('inf')
            
            # Find the closest state
            for state, center in state_centers.items():
                dist = self.haversine_distance(lat, lon, center[0], center[1])
                if dist < closest_dist:
                    closest_dist = dist
                    closest_state = state
            
            if closest_state:
                # Determine region from the closest state
                for region, states in us_regions.items():
                    if closest_state in states:
                        user_region = region
                        break
            
            logger.info(f"Determined user is in region: {user_region}, closest state: {closest_state}")
            
            # Get all centers in the user's region
            centers_to_check = []
            for state in us_regions.get(user_region, []):
                if state in real_centers:
                    centers_to_check.extend(real_centers[state])
            
            # If we didn't find any centers in the region, check all centers
            if not centers_to_check:
                logger.warning(f"No centers found in region {user_region}, checking all centers")
                for state_centers in real_centers.values():
                    centers_to_check.extend(state_centers)
            
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