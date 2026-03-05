"""
FIFA Stats Platform - AI Analyzer Service
=========================================
Analyzes FIFA match screenshots using Google Gemini AI to extract match statistics.
"""

import os
import logging
from typing import Dict, Any
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
        self.allow_fallback_scoring = os.getenv('ALLOW_FALLBACK_SCORING', 'false').lower() == 'true'
        if GENAI_AVAILABLE:
            self._configure_model()
    
    def _configure_model(self, api_key: str = None) -> None:
        """Configure the Gemini model with a provided key (or next available key)."""
        api_key = api_key or api_key_manager.get_key()
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("AI Analyzer configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure AI model: {e}")
                self.model = None

    def _get_candidate_keys(self):
        """Return API keys to try in order."""
        return list(api_key_manager.keys or [])
    
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
        
        candidate_keys = self._get_candidate_keys()
        if not candidate_keys:
            logger.warning("No Gemini API keys configured")
            return self._fallback_analysis()
        
        # Create the prompt once
        prompt = """You are a strict FIFA/football match statistics validator.
Only set is_valid_screenshot=true if this image clearly shows a real football match stats/result screen.
If the image is a person photo, selfie, unrelated content, text-only poster, document, or unclear content, set is_valid_screenshot=false.
Analyze this image and extract:

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

        last_error = None
        for api_key in candidate_keys:
            try:
                self._configure_model(api_key=api_key)
                if not self.model:
                    api_key_manager.record_usage(api_key, success=False)
                    continue

                myfile = genai.upload_file(image_path)
                response = self.model.generate_content([myfile, prompt])
                result = self._parse_ai_response(response.text)
                api_key_manager.record_usage(api_key, success=True)
                return result
            except Exception as e:
                last_error = e
                logger.error(f"Error analyzing screenshot with key {api_key[:10]}...: {e}")
                api_key_manager.record_usage(api_key, success=False)
                continue

        if last_error:
            logger.error(f"All API keys failed for AI analysis: {last_error}")
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

                parsed = {
                    'success': True,
                    'is_valid_screenshot': bool(data.get('is_valid_screenshot', False)),
                    'goals': int(data.get('goals', 0) or 0),
                    'assists': int(data.get('assists', 0) or 0),
                    'possession': int(data.get('possession', 0) or 0),
                    'shots': int(data.get('shots', 0) or 0),
                    'shots_on_target': int(data.get('shots_on_target', 0) or 0),
                    'pass_accuracy': int(data.get('pass_accuracy', 0) or 0),
                    'tackles': int(data.get('tackles', 0) or 0),
                    'analysis_notes': data.get('analysis_notes', '')
                }
                return self._validate_stats(parsed)
            
            # If no JSON found, return fallback
            return self._fallback_analysis()
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_analysis()

    def _validate_stats(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted stats and reject suspicious/non-match data."""
        if not result.get('is_valid_screenshot', False):
            return result

        goals = int(result.get('goals', 0))
        assists = int(result.get('assists', 0))
        possession = int(result.get('possession', 0))
        shots = int(result.get('shots', 0))
        shots_on_target = int(result.get('shots_on_target', 0))
        pass_accuracy = int(result.get('pass_accuracy', 0))
        tackles = int(result.get('tackles', 0))

        ranges_ok = (
            0 <= goals <= 20 and
            0 <= assists <= 20 and
            0 <= possession <= 100 and
            0 <= shots <= 60 and
            0 <= shots_on_target <= 40 and
            shots_on_target <= shots and
            0 <= pass_accuracy <= 100 and
            0 <= tackles <= 50
        )

        if not ranges_ok:
            result['is_valid_screenshot'] = False
            result['analysis_notes'] = 'Invalid stats range detected; rejected.'
        return result
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """
        Provide fallback analysis when AI is unavailable.
        
        Returns:
            Dict with simulated statistics for testing
        """
        if not self.allow_fallback_scoring:
            return {
                'success': False,
                'is_valid_screenshot': False,
                'analysis_notes': 'AI unavailable and fallback scoring is disabled',
                'error': 'AI validation unavailable',
                'is_fallback': True
            }

        # Optional debug-only fallback mode.
        return {
            'success': True,
            'is_valid_screenshot': False,
            'goals': 0,
            'assists': 0,
            'possession': 0,
            'shots': 0,
            'shots_on_target': 0,
            'pass_accuracy': 0,
            'tackles': 0,
            'analysis_notes': 'Fallback mode enabled; no points for unverified image',
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

