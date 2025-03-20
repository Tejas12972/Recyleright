"""
Utility for converting TensorFlow models to TensorFlow Lite format.
"""

import logging
import os
import tensorflow as tf

logger = logging.getLogger(__name__)

def convert_to_tflite(model_path, output_path, quantize=True):
    """
    Convert a TensorFlow model to TensorFlow Lite format.
    
    Args:
        model_path (str): Path to the TensorFlow model.
        output_path (str): Path to save the TensorFlow Lite model.
        quantize (bool): Whether to quantize the model.
        
    Returns:
        bool: True if conversion was successful, False otherwise.
    """
    try:
        # Load the TensorFlow model
        logger.info(f"Loading TensorFlow model from {model_path}")
        model = tf.keras.models.load_model(model_path)
        
        # Create a converter
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Apply optimization if requested
        if quantize:
            logger.info("Applying post-training quantization")
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
        
        # Convert the model
        logger.info("Converting model to TensorFlow Lite format")
        tflite_model = converter.convert()
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the model
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        logger.info(f"TensorFlow Lite model saved to {output_path}")
        
        # Calculate size reduction
        original_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        lite_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        reduction = (original_size - lite_size) / original_size * 100
        
        logger.info(f"Model size reduced from {original_size:.2f}MB to {lite_size:.2f}MB ({reduction:.2f}% reduction)")
        
        return True
    except Exception as e:
        logger.error(f"Error converting model to TFLite: {e}", exc_info=True)
        return False

def optimize_for_int8(model_path, output_path, representative_dataset):
    """
    Optimize a TensorFlow model for int8 quantization.
    
    Args:
        model_path (str): Path to the TensorFlow model.
        output_path (str): Path to save the TensorFlow Lite model.
        representative_dataset: A generator that yields representative data for calibration.
        
    Returns:
        bool: True if optimization was successful, False otherwise.
    """
    try:
        # Load the TensorFlow model
        logger.info(f"Loading TensorFlow model from {model_path}")
        model = tf.keras.models.load_model(model_path)
        
        # Create a converter
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Configure the converter for int8 quantization
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = representative_dataset
        
        # Force conversion to int8
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
        
        # Convert the model
        logger.info("Converting model to int8 quantized TensorFlow Lite format")
        tflite_model = converter.convert()
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the model
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        logger.info(f"Int8 quantized TensorFlow Lite model saved to {output_path}")
        
        # Calculate size reduction
        original_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        lite_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        reduction = (original_size - lite_size) / original_size * 100
        
        logger.info(f"Model size reduced from {original_size:.2f}MB to {lite_size:.2f}MB ({reduction:.2f}% reduction)")
        
        return True
    except Exception as e:
        logger.error(f"Error optimizing model for int8: {e}", exc_info=True)
        return False 