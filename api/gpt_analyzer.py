"""
ChatGPT Integration for RecycleRight image analysis.
"""

import os
import base64
import logging
import openai
import config

logger = logging.getLogger(__name__)

class GPTImageAnalyzer:
    """
    Analyzes images using OpenAI's GPT-4o Vision capabilities to determine
    recyclability and proper disposal methods.
    """
    
    def __init__(self):
        """Initialize the GPT analyzer with API key."""
        self.api_key = config.OPENAI_API_KEY
        self.model = config.GPT_MODEL
        
        if not self.api_key:
            logger.error("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
            raise ValueError("OpenAI API key not configured")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info(f"GPT Image Analyzer initialized with model: {self.model}")
    
    def _encode_image(self, image_path):
        """
        Encode an image to base64 for sending to OpenAI API.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Base64 encoded image
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise
    
    def analyze_image(self, image_path):
        """
        Analyze an image using GPT-4o to determine recyclability.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            dict: Analysis results including material composition, recyclability, and disposal suggestions
        """
        try:
            # Encode image to base64
            base64_image = self._encode_image(image_path)
            
            # System prompt for recycling analysis
            system_prompt = """As a recycling expert for Recycleright, analyze an image to determine its composition and recyclability, then provide suggestions for proper disposal.

First, analyze the image to identify materials, considering common categories such as glass, metal, plastic, and paper. Evaluate the identified materials for their recyclability based on the standard recycling guidelines.

# Steps

1. **Analyze the Image**: 
   - Identify the items and materials present in the image.
   - Categorize items into common material groups: plastic, paper, metal, glass, or mixed materials.

2. **Determine Recyclability**:
   - Use standard recycling guidelines to determine the recyclability of each material found.
   - Consider any contaminants that may affect recyclability, such as food residue on paper.

3. **Provide Suggestions for Disposal**:
   - Suggest appropriate recycling methods for the recyclable materials identified.
   - Offer alternatives for materials that cannot be recycled, e.g., upcycling or proper waste disposal methods.

# Output Format

Respond in a structured format:
- Material Composition: List of identified materials.
- Recyclability: Status of each material (e.g., recyclable, not recyclable).
- Disposal Suggestions: Recommendations for each material's disposal.

# Notes

- Always consider local recycling guidelines, as they may vary.
- Contaminants can affect the recyclability, so items should be clean and dry before recycling."""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze this image and tell me if it's recyclable and how I should dispose of it:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Extract the response text
            analysis_text = response.choices[0].message.content
            logger.info(f"Image analysis complete. Response length: {len(analysis_text)}")
            
            # Parse the response into structured data
            parsed_result = self._parse_response(analysis_text)
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error analyzing image with GPT-4o: {e}", exc_info=True)
            return {
                "error": f"Error analyzing image: {str(e)}",
                "material_composition": [],
                "recyclability": [],
                "disposal_suggestions": []
            }
    
    def _parse_response(self, response_text):
        """
        Parse the response from GPT-4o into structured data.
        
        Args:
            response_text (str): The text response from GPT-4o
            
        Returns:
            dict: Structured data with material_composition, recyclability, and disposal_suggestions
        """
        try:
            # Initialize results
            result = {
                "material_composition": [],
                "recyclability": [],
                "disposal_suggestions": []
            }
            
            # Look for the sections in the response
            sections = {
                "Material Composition": "material_composition",
                "Recyclability": "recyclability",
                "Disposal Suggestions": "disposal_suggestions"
            }
            
            current_section = None
            
            # Split by lines and process
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a section header
                for header, key in sections.items():
                    if line.lower().startswith(header.lower()) or line == f"**{header}**:" or line == f"- **{header}**:":
                        current_section = key
                        break
                
                # If we're in a section and this is a bullet point, add it to the result
                if current_section and (line.startswith('-') or line.startswith('*')):
                    # Clean up the line
                    clean_line = line.lstrip('-* ').strip()
                    if clean_line and not any(header.lower() in clean_line.lower() for header in sections.keys()):
                        result[current_section].append(clean_line)
            
            # If we couldn't parse structured data, return the whole response
            if not any(result.values()):
                # Just split by the headers as best we can
                for header, key in sections.items():
                    # Find the header in the text
                    start_idx = response_text.lower().find(header.lower())
                    if start_idx >= 0:
                        # Find the next header or the end of the text
                        next_headers = [h.lower() for h in sections.keys() if h.lower() != header.lower()]
                        next_indices = [response_text.lower().find(h, start_idx + len(header)) for h in next_headers]
                        next_indices = [i for i in next_indices if i >= 0]
                        
                        end_idx = min(next_indices) if next_indices else len(response_text)
                        section_text = response_text[start_idx + len(header):end_idx].strip()
                        
                        # Split by lines or bullet points
                        for line in section_text.split('\n'):
                            line = line.strip()
                            if line and line.startswith(('-', '*')) and not any(h.lower() in line.lower() for h in sections.keys()):
                                result[key].append(line.lstrip('-* ').strip())
            
            # Determine waste type (recyclable, compostable, trash)
            waste_type = self._determine_waste_type(result)
            result["waste_type"] = waste_type
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing GPT-4o response: {e}", exc_info=True)
            return {
                "error": f"Error parsing analysis: {str(e)}",
                "material_composition": [],
                "recyclability": [],
                "disposal_suggestions": [],
                "waste_type": "unknown"
            }
    
    def _determine_waste_type(self, parsed_response):
        """
        Determine the overall waste type based on the parsed response.
        
        Args:
            parsed_response (dict): The parsed response from GPT-4o
            
        Returns:
            str: One of 'recyclable', 'compostable', 'trash', or 'mixed'
        """
        # Check recyclability section for determination
        recyclability = ' '.join(parsed_response.get('recyclability', [])).lower()
        
        # Count keywords to determine type
        recyclable_keywords = ['recyclable', 'can be recycled', 'recycle']
        compostable_keywords = ['compostable', 'can be composted', 'compost']
        trash_keywords = ['not recyclable', 'trash', 'landfill', 'cannot be recycled']
        
        recyclable_count = sum(1 for keyword in recyclable_keywords if keyword in recyclability)
        compostable_count = sum(1 for keyword in compostable_keywords if keyword in recyclability)
        trash_count = sum(1 for keyword in trash_keywords if keyword in recyclability)
        
        # If there are multiple types, consider it mixed
        if recyclable_count > 0 and (compostable_count > 0 or trash_count > 0):
            return "mixed"
        elif recyclable_count > 0:
            return "recyclable"
        elif compostable_count > 0:
            return "compostable"
        elif trash_count > 0:
            return "trash"
        else:
            # If we can't determine, check disposal suggestions
            disposal = ' '.join(parsed_response.get('disposal_suggestions', [])).lower()
            
            if any(keyword in disposal for keyword in recyclable_keywords):
                return "recyclable"
            elif any(keyword in disposal for keyword in compostable_keywords):
                return "compostable"
            elif any(keyword in disposal for keyword in trash_keywords):
                return "trash"
            
            # Default to mixed if we can't determine
            return "mixed" 