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
            # Check if file exists
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                raise FileNotFoundError(f"Image file not found: {image_path}")
                
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
            # Check if file exists and is readable
            if not os.path.isfile(image_path):
                logger.error(f"Image file not found or not accessible: {image_path}")
                return {
                    "error": f"Image file not found or not accessible: {image_path}",
                    "material_composition": [],
                    "recyclability": [],
                    "disposal_suggestions": [],
                    "waste_type": "unknown"
                }
            
            # Encode image to base64
            base64_image = self._encode_image(image_path)
            
            # System prompt for recycling analysis
            system_prompt = """Analyze the uploaded image and identify the waste material shown. Focus on visual characteristics, textures, labels, and shapes to determine:

1. Material Composition: Provide specific, detailed identification of materials present (e.g., "HDPE plastic milk jug" rather than just "plastic" or "PET plastic water bottle with paper label" rather than just "bottle").

2. Recyclability Assessment: For each identified material, clearly state whether it is:
   - RECYCLABLE (in most standard municipal programs)
   - CONDITIONALLY RECYCLABLE (requires special handling/facilities)
   - NOT RECYCLABLE

3. Disposal Suggestions: Provide actionable, specific instructions for proper disposal of each material component.

4. Confidence Level: Indicate your confidence in the analysis (High/Medium/Low).

If multiple materials are present, analyze each component separately. If the image is unclear or the material cannot be confidently identified, acknowledge this limitation and provide best recommendations based on visual cues.

Return results in a structured format without markdown formatting that can be directly parsed into my website fields."""
            
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
                            {"type": "text", "text": "Analyze this waste material for recyclability:"},
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
                max_tokens=2048,
                temperature=0.3,  # Lower temperature for more deterministic results
                top_p=1.0  # Control nucleus sampling
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
                "Recyclability Assessment": "recyclability",
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
                section_found = False
                for header, key in sections.items():
                    if line.lower().startswith(header.lower()) or ":" in line and line.split(":")[0].strip().lower() == header.lower():
                        current_section = key
                        section_found = True
                        # Extract the value if it's on the same line (like "Material Composition: PET plastic")
                        if ":" in line:
                            value = line.split(":", 1)[1].strip()
                            if value:
                                result[key].append(value)
                        break
                
                # Skip processing this line if it was a section header
                if section_found:
                    continue
                
                # If we're in a section and this is a bullet point or content line, add it to the result
                if current_section:
                    # Clean up the line - remove bullet points and list markers
                    clean_line = line
                    if line.startswith('-') or line.startswith('*'):
                        clean_line = line.lstrip('-* ').strip()
                    elif line.startswith(('•', '○', '▪', '▫', '◦')):
                        clean_line = line[1:].strip()
                    
                    # Only add non-empty lines that don't contain section headers
                    if clean_line and not any(header.lower() in clean_line.lower() for header in sections.keys()):
                        result[current_section].append(clean_line)
            
            # If we couldn't parse structured data, try a more aggressive approach
            if not any(result.values()):
                for header, key in sections.items():
                    start_idx = response_text.lower().find(header.lower())
                    if start_idx >= 0:
                        # Find the next header or the end of the text
                        next_headers = [(h.lower(), response_text.lower().find(h.lower(), start_idx + len(header))) 
                                       for h in sections.keys() if h.lower() != header.lower()]
                        next_headers = [(h, i) for h, i in next_headers if i > 0]
                        
                        end_idx = min([i for _, i in next_headers]) if next_headers else len(response_text)
                        section_text = response_text[start_idx + len(header):end_idx].strip().lstrip(':-').strip()
                        
                        # Split by newlines and add each line
                        for line in section_text.split('\n'):
                            line = line.strip()
                            if line and not any(h.lower() in line.lower() for h in sections.keys()):
                                # Remove bullet points
                                if line.startswith(('-', '*', '•', '○', '▪', '▫', '◦')):
                                    line = line[1:].strip()
                                result[key].append(line)
            
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
        if (recyclable_count > 0 and trash_count > 0) or (compostable_count > 0 and trash_count > 0):
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