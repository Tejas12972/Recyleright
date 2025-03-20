"""
Waste classification module using TensorFlow Lite.
"""

import logging
import os
import numpy as np
import cv2
import tensorflow as tf

# Add parent directory to path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config

logger = logging.getLogger(__name__)

class WasteClassifier:
    """Class for waste classification using TensorFlow Lite."""
    
    def __init__(self, model_path, labels_path):
        """
        Initialize the waste classifier.
        
        Args:
            model_path (str): Path to the TensorFlow Lite model file.
            labels_path (str): Path to the labels file.
        """
        self.model_path = model_path
        self.labels_path = labels_path
        self.input_size = config.INPUT_SIZE
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        
        self._load_model()
        self._load_labels()
        
        logger.info(f"Waste classifier initialized with model: {model_path}")
    
    def _load_model(self):
        """Load TensorFlow Lite model."""
        try:
            # Load the TFLite model
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info("TensorFlow Lite model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading TensorFlow Lite model: {e}", exc_info=True)
            raise
    
    def _load_labels(self):
        """Load class labels."""
        try:
            with open(self.labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
            logger.info(f"Loaded {len(self.labels)} class labels")
        except Exception as e:
            logger.error(f"Error loading labels: {e}", exc_info=True)
            raise
    
    def preprocess_image(self, image):
        """
        Preprocess image for model input.
        
        Args:
            image: Input image (numpy array).
            
        Returns:
            Preprocessed image ready for model input.
        """
        # Resize image to required input dimensions
        resized = cv2.resize(image, self.input_size)
        
        # Convert to RGB if it's BGR (OpenCV default)
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        
        # Apply ImageNet normalization if using a pretrained model
        for i in range(3):
            normalized[:, :, i] = (normalized[:, :, i] - config.NORMALIZE_MEAN[i]) / config.NORMALIZE_STD[i]
        
        # Add batch dimension
        input_data = np.expand_dims(normalized, axis=0)
        
        return input_data
    
    def classify(self, image):
        """
        Classify a waste item in an image.
        
        Args:
            image: Input image (numpy array).
            
        Returns:
            A list of (class_name, probability) tuples sorted by probability.
        """
        # Preprocess the image
        input_data = self.preprocess_image(image)
        
        # Set the input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        
        # Run inference
        self.interpreter.invoke()
        
        # Get the output tensor
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        scores = output_data[0]
        
        # Create a list of (label, score) tuples
        results = []
        for i, score in enumerate(scores):
            if i < len(self.labels) and score >= self.confidence_threshold:
                results.append((self.labels[i], float(score)))
        
        # Sort by score in descending order
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Classification complete. Found {len(results)} results above threshold.")
        return results
    
    def get_top_prediction(self, image):
        """
        Get the top prediction for an image.
        
        Args:
            image: Input image (numpy array).
            
        Returns:
            Tuple of (class_name, probability) or (None, 0) if no predictions above threshold.
        """
        results = self.classify(image)
        if results:
            return results[0]
        return (None, 0) 