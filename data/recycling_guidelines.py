"""
Recycling guidelines module for RecycleRight application.
"""

import logging
import json
import os

# Add parent directory to path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class RecyclingGuidelines:
    """Class for handling recycling guidelines and recommendations."""
    
    def __init__(self, db):
        """
        Initialize the recycling guidelines manager.
        
        Args:
            db: Database instance.
        """
        self.db = db
        
        # Ensure default guidelines are loaded
        self._load_default_guidelines()
    
    def _load_default_guidelines(self):
        """Load default recycling guidelines into the database if they don't exist."""
        try:
            # Check if guidelines already exist
            self.db.cursor.execute("SELECT COUNT(*) FROM recycling_guidelines")
            count = self.db.cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Found {count} existing recycling guidelines in database")
                return
            
            # Define default guidelines for common waste types
            default_guidelines = [
                # Plastic
                {
                    "waste_type": "plastic_PET",
                    "region": "default",
                    "instructions": "Rinse containers and remove caps before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "plastic_HDPE",
                    "region": "default",
                    "instructions": "Rinse containers before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "plastic_PVC",
                    "region": "default",
                    "instructions": "PVC is not commonly accepted in curbside recycling.",
                    "recyclable": False,
                    "special_handling": "Take to specialized recycling centers"
                },
                {
                    "waste_type": "plastic_LDPE",
                    "region": "default",
                    "instructions": "Plastic bags and films are not accepted in most curbside programs.",
                    "recyclable": False,
                    "special_handling": "Take to specialized recycling centers or store drop-off locations"
                },
                {
                    "waste_type": "plastic_PP",
                    "region": "default",
                    "instructions": "Rinse containers before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "plastic_PS",
                    "region": "default",
                    "instructions": "Polystyrene is not accepted in most curbside recycling programs.",
                    "recyclable": False,
                    "special_handling": "Consider reuse or specialized drop-off"
                },
                
                # Paper
                {
                    "waste_type": "paper",
                    "region": "default",
                    "instructions": "Clean paper can be recycled. Remove staples, clips, and other non-paper items.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "cardboard",
                    "region": "default",
                    "instructions": "Flatten cardboard boxes before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "paper_carton",
                    "region": "default",
                    "instructions": "Rinse cartons and flatten before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                
                # Metal
                {
                    "waste_type": "metal_aluminum",
                    "region": "default",
                    "instructions": "Rinse cans before recycling.",
                    "recyclable": True,
                    "special_handling": None
                },
                {
                    "waste_type": "metal_steel",
                    "region": "default",
                    "instructions": "Rinse cans before recycling. Labels can stay on.",
                    "recyclable": True,
                    "special_handling": None
                },
                
                # Glass
                {
                    "waste_type": "glass",
                    "region": "default",
                    "instructions": "Rinse glass containers before recycling. Remove caps and lids.",
                    "recyclable": True,
                    "special_handling": "May need to be sorted by color in some regions"
                },
                
                # Organic waste
                {
                    "waste_type": "organic_food",
                    "region": "default",
                    "instructions": "Food waste should be composted if possible.",
                    "recyclable": False,
                    "special_handling": "Compost or municipal organic waste collection"
                },
                {
                    "waste_type": "organic_yard",
                    "region": "default",
                    "instructions": "Yard waste should be composted or collected separately.",
                    "recyclable": False,
                    "special_handling": "Compost or municipal yard waste collection"
                },
                
                # E-waste
                {
                    "waste_type": "e_waste",
                    "region": "default",
                    "instructions": "Electronic waste should never be placed in regular trash or recycling.",
                    "recyclable": False,
                    "special_handling": "Take to e-waste collection events or certified recyclers"
                },
                
                # Hazardous waste
                {
                    "waste_type": "hazardous",
                    "region": "default",
                    "instructions": "Hazardous materials should never be placed in regular trash or recycling.",
                    "recyclable": False,
                    "special_handling": "Take to hazardous waste collection facilities"
                },
                
                # Non-recyclable
                {
                    "waste_type": "non_recyclable",
                    "region": "default",
                    "instructions": "This item is not recyclable in most programs.",
                    "recyclable": False,
                    "special_handling": "Dispose in regular trash"
                }
            ]
            
            # Add region-specific variations
            urban_variations = [
                {
                    "waste_type": "plastic_LDPE",
                    "region": "urban",
                    "instructions": "Some urban areas accept plastic films in separate collection.",
                    "recyclable": True,
                    "special_handling": "Check local guidelines"
                },
                {
                    "waste_type": "plastic_PS",
                    "region": "urban",
                    "instructions": "Some urban areas have polystyrene recycling programs.",
                    "recyclable": True,
                    "special_handling": "Check local guidelines"
                }
            ]
            
            # Insert all the guidelines into the database
            for guideline in default_guidelines + urban_variations:
                self.db.cursor.execute('''
                INSERT INTO recycling_guidelines 
                (waste_type, region, instructions, recyclable, special_handling)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    guideline["waste_type"],
                    guideline["region"],
                    guideline["instructions"],
                    guideline["recyclable"],
                    guideline["special_handling"]
                ))
            
            self.db.conn.commit()
            logger.info(f"Added {len(default_guidelines) + len(urban_variations)} default recycling guidelines to database")
        except Exception as e:
            logger.error(f"Error loading default recycling guidelines: {e}", exc_info=True)
            self.db.conn.rollback()
    
    def get_guidelines(self, waste_type, region=None):
        """
        Get recycling guidelines for a specific waste type and region.
        
        Args:
            waste_type (str): Type of waste material.
            region (str): Geographic region code. If None, uses 'default'.
            
        Returns:
            dict: Guidelines for handling this waste type.
        """
        if region is None:
            region = "default"
        
        guidelines = self.db.get_recycling_guidelines(waste_type, region)
        
        if not guidelines and region != "default":
            # Fall back to default guidelines if region-specific ones aren't found
            guidelines = self.db.get_recycling_guidelines(waste_type, "default")
        
        if not guidelines:
            # If still no guidelines, use generic non-recyclable guidelines
            guidelines = self.db.get_recycling_guidelines("non_recyclable", "default")
        
        logger.info(f"Retrieved recycling guidelines for {waste_type} in {region}")
        return guidelines
    
    def get_disposal_instructions(self, waste_type, region=None):
        """
        Get simplified disposal instructions for a waste type.
        
        Args:
            waste_type (str): Type of waste material.
            region (str): Geographic region code.
            
        Returns:
            dict: Simplified disposal instructions.
        """
        guidelines = self.get_guidelines(waste_type, region)
        
        if not guidelines:
            return {
                "recyclable": False,
                "instructions": "Unable to find guidelines for this material. Please check with local authorities.",
                "disposal_method": "unknown"
            }
        
        # Determine the appropriate disposal method
        if guidelines["recyclable"]:
            disposal_method = "recycle"
        elif "compost" in guidelines["instructions"].lower() or (
                guidelines["special_handling"] and "compost" in guidelines["special_handling"].lower()):
            disposal_method = "compost"
        elif guidelines["waste_type"].startswith("hazardous") or guidelines["waste_type"].startswith("e_waste"):
            disposal_method = "special_collection"
        else:
            disposal_method = "trash"
        
        return {
            "recyclable": guidelines["recyclable"],
            "instructions": guidelines["instructions"],
            "special_handling": guidelines["special_handling"],
            "disposal_method": disposal_method
        } 