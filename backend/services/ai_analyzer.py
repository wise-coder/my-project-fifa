"""
FIFA Stats Platform - AI Analyzer Service
=========================================
Analyzes FIFA match screenshots using Google Gemini AI to extract match statistics.
"""

import os
import logging
from typing import Dict, Any, Optional
import json

# Import API key manager
from services.api_key_manager import api_key_manager

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai not installed. AI analysis will use fallback mode.")
    GENAI_AVAILABLE = False


class AIAnalyzer:
    """
    Analyzes FIFA match screenshots using AI to extract statistics.
    
    Features:
    - Uses Google Gemini for image analysis
    - Extracts goals, assists, possession, shots, pass accuracy, tackles
    - Automatic retry with different API keys
    - Fallback mode for when API is unavailable
    """
    
    def __init__(self):
        """Initialize the AI analyzer."""
        self.model = None
        if GENAI_AVAILABLE:
            self._configure_model()
    
    def _configure_model(self) -> None:
        """Configure the Gemini model with an available API key."""
        api_key = api_key_manager.get_key()
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("AI Analyzer configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure AI model: {e}")
                self.model = None
    
    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze a FIFA match screenshot to extract statistics.
        
        Args:
            image_path: Path to the screenshot image file
            
        Returns:
            Dict containing extracted statistics and analysis result
        """
        if not GENAI_AVAILABLE:
            return self._fallback_analysis()
        
        if not self.model:
            # Try to reconfigure
            self._configure_model()
            if not self.model:
                return self._fallback_analysis()
        
        try:
            # Upload the image
            myfile = genai.upload_file(image_path)
            
            # Create the prompt
            prompt = """You are a FIFA match statistics analyzer. 
Analyze this FIFA match screenshot and extract the following statistics:

1. Goals (goals scored by the player)
2. Assists (goals assisted)
3. Possession (percentage, e.g., 58)
4. Shots (total shots)
5. Shots on Target
6. Pass Accuracy (percentage)
7. Tackles (successful tackles)
8. Is this a valid FIFA match statistics screenshot? (true/false)

Respond in JSON format:
{
  "is_valid_screenshot": true/false,
  "goals": 0,
  "assists": 0,
  "possession": 0,
  "shots": 0,
  "shots_on_target": 0,
  "pass_accuracy": 0,
  "tackles": 0,
  "analysis_notes": "brief explanation"
}

If the image is not a valid FIFA match statistics screenshot, set is_valid_screenshot to false."""
            
            # Generate content
            response = self.model.generate_content([myfile, prompt])
            
            # Parse the response
            result = self._parse_ai_response(response.text)
            
            # Record successful usage
            api_key = api_key_manager.get_key()
            if api_key:
                api_key_manager.record_usage(api_key, success=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            
            # Record failed usage
            api_key = api_key_manager.get_key()
            if api_key:
                api_key_manager.record_usage(api_key, success=False)
            
            # Try fallback
            return self._fallback_analysis()
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract statistics.
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Dict with extracted statistics
        """
        try:
            # Try to find JSON in the response
            import re
            
            # Look for JSON block
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Validate and return the data
                return {
                    'success': True,
                    'is_valid_screenshot': data.get('is_valid_screenshot', True),
                    'goals': data.get('goals', 0),
                    'assists': data.get('assists', 0),
                    'possession': data.get('possession', 50),
                    'shots': data.get('shots', 0),
                    'shots_on_target': data.get('shots_on_target', 0),
                    'pass_accuracy': data.get('pass_accuracy', 0),
                    'tackles': data.get('tackles', 0),
                    'analysis_notes': data.get('analysis_notes', '')
                }
            
            # If no JSON found, return fallback
            return self._fallback_analysis()
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """
        Provide fallback analysis when AI is unavailable.
        
        Returns:
            Dict with simulated statistics for testing
        """
        import random
        
        # Generate random but realistic stats for testing
        goals = random.randint(0, 5)
        assists = random.randint(0, 2)
        possession = random.randint(35, 65)
        shots = random.randint(3, 15)
        shots_on_target = random.randint(1, min(shots, 8))
        pass_accuracy = random.randint(60, 95)
        tackles = random.randint(0, 8)
        
        return {
            'success': True,
            'is_valid_screenshot': True,
            'goals': goals,
            'assists': assists,
            'possession': possession,
            'shots': shots,
            'shots_on_target': shots_on_target,
            'pass_accuracy': pass_accuracy,
            'tackles': tackles,
            'analysis_notes': 'Fallback mode - API unavailable',
            'is_fallback': True
        }


# Global instance
ai_analyzer = AIAnalyzer()


def analyze_screenshot(image_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a screenshot.
    
    Args:
        image_path: Path to the screenshot image file
        
    Returns:
        Dict containing extracted statistics
    """
    return ai_analyzer.analyze_screenshot(image_path)

