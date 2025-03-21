"""
Waste Classifier for RecycleRight application.

This module contains the WasteClassifier class that handles the classification
of waste items using a TensorFlow Lite model.
"""

import os
import logging
import numpy as np
import cv2
from pathlib import Path

# Import config using importlib to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location("config", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app/config.py"))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

logger = logging.getLogger(__name__)

class WasteClassifier:
    """
    Class for classifying waste items using a TensorFlow Lite model.
    """
    
    def __init__(self, model_path, labels_path):
        """
        Initialize the waste classifier.
        
        Args:
            model_path (str): Path to the TensorFlow Lite model
            labels_path (str): Path to the labels file
        """
        self.model_path = model_path
        self.labels_path = labels_path
        self.input_size = (224, 224)  # Default input size for most models
        self.confidence_threshold = 0.7  # Default confidence threshold
        
        logger.info(f"Initializing WasteClassifier with model: {model_path}")
        
        # Load labels
        self.labels = self._load_labels()
        
        # In a real implementation, we would load the TensorFlow Lite model here
        # For this prototype, we'll simulate classification
        
        logger.info("WasteClassifier initialized successfully")
    
    def _load_labels(self):
        """
        Load labels from the labels file.
        
        Returns:
            list: List of label strings
        """
        try:
            if os.path.exists(self.labels_path):
                with open(self.labels_path, 'r') as f:
                    return [line.strip() for line in f.readlines()]
            else:
                # Return default labels if file doesn't exist
                logger.warning(f"Labels file not found at {self.labels_path}. Using default labels.")
                return [
                    "plastic_PET", "plastic_HDPE", "plastic_PVC", "plastic_LDPE", 
                    "plastic_PP", "plastic_PS", "glass", "paper", "cardboard", 
                    "metal", "organic", "electronic", "batteries", "hazardous"
                ]
        except Exception as e:
            logger.error(f"Error loading labels: {e}")
            return []
    
    def preprocess_image(self, image):
        """
        Preprocess the image for model input.
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            numpy.ndarray: Preprocessed image
        """
        # Resize image to input size
        resized = cv2.resize(image, self.input_size)
        
        # Convert to RGB if it's BGR
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize pixel values
        normalized = resized.astype(np.float32) / 255.0
        
        # Add batch dimension
        return np.expand_dims(normalized, axis=0)
    
    def get_top_prediction(self, image):
        """
        Get the top waste type prediction for an image.
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            tuple: (waste_type, confidence)
        """
        try:
            # In a real implementation, we would:
            # 1. Preprocess the image
            # 2. Run inference with the TensorFlow Lite model
            # 3. Process the output to get the top prediction
            
            # For this prototype, we'll simulate a classification result
            # based on the image characteristics to provide a realistic demo
            
            # Simple image analysis to make a pseudo-prediction
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            avg_hue = np.mean(hsv_image[:, :, 0])
            avg_saturation = np.mean(hsv_image[:, :, 1])
            avg_value = np.mean(hsv_image[:, :, 2])
            
            # Make a pseudo-decision based on image colors
            if 20 <= avg_hue <= 40 and avg_saturation > 50:  # Yellowish
                waste_type = "plastic_HDPE"
                confidence = 0.82
            elif 40 <= avg_hue <= 70 and avg_saturation > 30:  # Greenish
                waste_type = "glass"
                confidence = 0.91
            elif avg_hue < 20 and avg_value < 100:  # Brownish
                waste_type = "cardboard"
                confidence = 0.88
            elif 90 <= avg_hue <= 130 and avg_saturation > 50:  # Blueish
                waste_type = "plastic_PET"
                confidence = 0.86
            elif avg_value > 200 and avg_saturation < 30:  # Very bright, low saturation
                waste_type = "paper"
                confidence = 0.79
            elif avg_value < 50:  # Very dark
                waste_type = "metal"
                confidence = 0.76
            else:
                # Default to a common type with moderate confidence
                waste_type = "plastic_PET"
                confidence = 0.72
            
            if confidence >= self.confidence_threshold:
                logger.info(f"Classified waste as {waste_type} with confidence {confidence:.2f}")
                return waste_type, confidence
            else:
                logger.info(f"Classification confidence too low: {confidence:.2f}")
                return None, confidence
                
        except Exception as e:
            logger.error(f"Error in classification: {e}", exc_info=True)
            return None, 0.0
    
    def get_all_predictions(self, image):
        """
        Get all waste type predictions for an image.
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            list: List of (waste_type, confidence) tuples
        """
        try:
            # Similar to get_top_prediction, but return multiple predictions
            # For the prototype, we'll return simulated results
            
            # Get the top prediction
            top_type, top_confidence = self.get_top_prediction(image)
            
            if not top_type:
                return []
            
            # Create a list of other predictions with lower confidence
            predictions = [
                (top_type, top_confidence)
            ]
            
            # Add some other types with lower confidence
            other_types = [t for t in self.labels if t != top_type]
            import random
            for i in range(3):  # Add 3 more predictions
                if other_types:
                    type_idx = random.randint(0, len(other_types) - 1)
                    waste_type = other_types.pop(type_idx)
                    confidence = max(0.2, min(0.65, top_confidence - (random.random() * 0.4)))
                    predictions.append((waste_type, confidence))
            
            # Sort by confidence
            return sorted(predictions, key=lambda x: x[1], reverse=True)
                
        except Exception as e:
            logger.error(f"Error getting all predictions: {e}", exc_info=True)
            return [] 