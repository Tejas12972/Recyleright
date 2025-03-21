"""
Waste classification model module for RecycleRight application.
"""

import os
import logging
import numpy as np
import cv2
import random
from pathlib import Path

import config

logger = logging.getLogger(__name__)

class WasteClassifier:
    """Waste classification model for identifying waste items."""
    
    def __init__(self, model_path=None, labels_path=None):
        """
        Initialize the waste classifier model.
        
        Args:
            model_path (str): Path to the TensorFlow Lite model file.
            labels_path (str): Path to the labels file.
        """
        self.model_path = model_path or config.MODEL_PATH
        self.labels_path = labels_path or config.LABELS_PATH
        self.labels_path_alt = getattr(config, 'LABELS_PATH_ALT', 'models/labels/waste_labels.txt')
        self.input_size = (224, 224)  # Default input size for model
        self.confidence_threshold = 0.6
        
        # Load labels
        self.labels = self._load_labels()
        
        logger.info(f"Initialized WasteClassifier with {len(self.labels)} labels")
    
    def _load_labels(self):
        """
        Load labels from file.
        
        Returns:
            list: List of label strings.
        """
        try:
            # Log the actual path being used
            logger.info(f"Attempting to load labels from: {self.labels_path}")
            
            # Check if path exists as absolute path
            if os.path.exists(self.labels_path):
                logger.info(f"Loading labels from: {self.labels_path}")
                with open(self.labels_path, 'r') as f:
                    return [line.strip() for line in f.readlines()]
            else:
                # Try the alternative path
                logger.info(f"Trying alternative path: {self.labels_path_alt}")
                if os.path.exists(self.labels_path_alt):
                    logger.info(f"Loading labels from: {self.labels_path_alt}")
                    with open(self.labels_path_alt, 'r') as f:
                        return [line.strip() for line in f.readlines()]
                else:
                    # Try relative to current file
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    full_path = os.path.join(base_dir, self.labels_path)
                    logger.info(f"Trying path relative to base dir: {full_path}")
                    
                    if os.path.exists(full_path):
                        logger.info(f"Loading labels from: {full_path}")
                        with open(full_path, 'r') as f:
                            return [line.strip() for line in f.readlines()]
                    else:
                        # Try the alternative path relative to base dir
                        alt_full_path = os.path.join(base_dir, self.labels_path_alt)
                        logger.info(f"Trying alternative path relative to base dir: {alt_full_path}")
                        
                        if os.path.exists(alt_full_path):
                            logger.info(f"Loading labels from: {alt_full_path}")
                            with open(alt_full_path, 'r') as f:
                                return [line.strip() for line in f.readlines()]
                        else:
                            logger.warning(f"Labels file not found at any of the attempted paths. Using default labels.")
                            # Default waste labels as fallback
                            return [
                                "plastic_bottle", "glass_bottle", "aluminum_can", "paper", "cardboard",
                                "plastic_bag", "food_waste", "styrofoam", "electronic_waste", "batteries",
                                "light_bulb", "clothing", "metal", "plastic_container", "tetra_pak"
                            ]
        except Exception as e:
            logger.error(f"Error loading labels: {e}", exc_info=True)
            return [
                "plastic_bottle", "glass_bottle", "aluminum_can", "paper", "cardboard",
                "plastic_bag", "food_waste", "styrofoam", "electronic_waste", "batteries",
                "light_bulb", "clothing", "metal", "plastic_container", "tetra_pak"
            ]
    
    def preprocess_image(self, image_path):
        """
        Preprocess image for model input.
        
        Args:
            image_path (str): Path to image file.
            
        Returns:
            numpy.ndarray: Preprocessed image.
        """
        try:
            # Read and resize image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image from {image_path}")
                return None
                
            img = cv2.resize(img, self.input_size)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Normalize to [0, 1]
            img = img / 255.0
            
            # Add batch dimension
            img = np.expand_dims(img, axis=0)
            
            return img
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}", exc_info=True)
            return None
    
    def get_top_prediction(self, image_path):
        """
        Get the top waste classification prediction for an image.
        
        Args:
            image_path (str): Path to image file.
            
        Returns:
            tuple: (waste_type, confidence) or (None, None) if prediction fails.
        """
        try:
            # In a real implementation, we would:
            # 1. Preprocess the image
            # 2. Run the model inference
            # 3. Process the results
            
            # Simulated response for demo purposes
            # Analyze image to make prediction more realistic
            try:
                img = cv2.imread(image_path)
                if img is None:
                    logger.error(f"Could not read image from {image_path}")
                    return None, None
                
                # Simple heuristics for demo
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                avg_hue = np.mean(hsv[:,:,0])
                avg_saturation = np.mean(hsv[:,:,1])
                
                # Assign waste types based on image characteristics
                if avg_hue < 30:  # Brownish
                    waste_type = "cardboard"
                    confidence = 0.85 + random.uniform(-0.1, 0.1)
                elif avg_hue < 60:  # Yellowish
                    waste_type = "paper"
                    confidence = 0.82 + random.uniform(-0.1, 0.1)
                elif avg_hue < 90:  # Greenish
                    waste_type = "glass_bottle"
                    confidence = 0.78 + random.uniform(-0.1, 0.1)
                elif avg_hue < 150:  # Bluish
                    waste_type = "plastic_bottle"
                    confidence = 0.88 + random.uniform(-0.1, 0.1)
                else:  # Other colors
                    if avg_saturation < 50:  # Low saturation - metals
                        waste_type = "aluminum_can"
                        confidence = 0.76 + random.uniform(-0.1, 0.1)
                    else:
                        waste_type = random.choice(["plastic_container", "plastic_bag", "styrofoam"])
                        confidence = 0.72 + random.uniform(-0.1, 0.1)
                        
            except Exception as img_e:
                logger.warning(f"Error analyzing image: {img_e}. Using random prediction.")
                # Fallback to random if image analysis fails
                waste_type = random.choice(self.labels)
                confidence = random.uniform(0.7, 0.95)
            
            return waste_type, confidence
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            return None, None
    
    def get_all_predictions(self, image_path):
        """
        Get all waste classification predictions for an image.
        
        Args:
            image_path (str): Path to image file.
            
        Returns:
            list: List of prediction dictionaries with 'label' and 'confidence' keys.
        """
        try:
            # Get top prediction first
            top_type, top_confidence = self.get_top_prediction(image_path)
            if not top_type:
                return []
                
            # Create a list with the top prediction and some random ones
            predictions = [{"label": top_type, "confidence": top_confidence}]
            
            # Add 2-4 more predictions with lower confidence
            num_additional = random.randint(2, 4)
            remaining_labels = [label for label in self.labels if label != top_type]
            
            for _ in range(num_additional):
                if not remaining_labels:
                    break
                
                rand_label = random.choice(remaining_labels)
                remaining_labels.remove(rand_label)
                
                # Lower confidence for additional predictions
                rand_confidence = top_confidence * random.uniform(0.3, 0.8)
                predictions.append({"label": rand_label, "confidence": rand_confidence})
            
            # Sort by confidence (descending)
            predictions.sort(key=lambda x: x["confidence"], reverse=True)
            
            return predictions
        except Exception as e:
            logger.error(f"Error getting all predictions: {e}", exc_info=True)
            return [] 