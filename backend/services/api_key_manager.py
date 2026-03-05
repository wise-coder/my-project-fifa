"""
FIFA Stats Platform - API Key Manager Service
=============================================
Manages multiple AI API keys for load balancing and rate limiting.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manages multiple AI API keys with automatic rotation and usage tracking.
    
    Features:
    - Load keys from environment variables
    - Track usage per key
    - Automatic key rotation
    - Fallback to backup keys
    """
    
    def __init__(self):
        """Initialize the API key manager and load keys from environment."""
        self.keys: List[str] = []
        self.key_usage: Dict[str, int] = {}
        self.key_errors: Dict[str, int] = {}
        self.current_key_index = 0
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load API keys from environment variables."""
        # Check for comma-separated keys first
        comma_keys = os.getenv('GEMINI_API_KEYS', '')
        if comma_keys:
            keys = [k.strip() for k in comma_keys.split(',') if k.strip()]
            self.keys.extend(keys)
            logger.info(f"Loaded {len(keys)} API keys from GEMINI_API_KEYS")
        
        # Check for individual keys
        for i in range(1, 5):
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key and key not in self.keys:
                self.keys.append(key)
        
        # Initialize usage tracking
        for key in self.keys:
            self.key_usage[key] = 0
            self.key_errors[key] = 0
        
        # Try to load from ocr.py as last resort
        if not self.keys:
            try:
                from ocr import API_KEY
                if API_KEY:
                    self.keys.append(API_KEY)
                    self.key_usage[API_KEY] = 0
                    logger.info("Loaded API key from ocr.py as fallback")
            except ImportError:
                pass
        
        logger.info(f"API Key Manager initialized with {len(self.keys)} keys")
    
    def get_key(self) -> Optional[str]:
        """
        Get the next available API key.
        
        Returns:
            str: An API key, or None if no keys are available
        """
        if not self.keys:
            logger.warning("No API keys available")
            return None
        
        # Try each key starting from current index
        for _ in range(len(self.keys)):
            key = self.keys[self.current_key_index]
            
            # Skip keys with too many errors
            if self.key_errors.get(key, 0) >= 5:
                self._rotate_key()
                continue
            
            return key
        
        # If all keys have errors, reset and return the first one
        logger.warning("All API keys have errors, resetting error counts")
        self.key_errors = {k: 0 for k in self.keys}
        return self.keys[0] if self.keys else None
    
    def _rotate_key(self) -> None:
        """Rotate to the next available key."""
        self.current_key_index = (self.current_key_index + 1) % len(self.keys) if self.keys else 0
    
    def record_usage(self, key: str, success: bool = True) -> None:
        """
        Record API key usage.
        
        Args:
            key: The API key that was used
            success: Whether the request was successful
        """
        if key in self.key_usage:
            self.key_usage[key] += 1
        
        if not success and key in self.key_errors:
            self.key_errors[key] += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for all API keys.
        
        Returns:
            Dict with usage statistics
        """
        total_usage = sum(self.key_usage.values())
        active_keys = sum(1 for k in self.keys if self.key_errors.get(k, 0) < 5)
        
        return {
            'total_keys': len(self.keys),
            'active_keys': active_keys,
            'total_requests': total_usage,
            'keys': [
                {
                    'prefix': key[:10] + '...' if len(key) > 10 else key,
                    'usage': self.key_usage.get(key, 0),
                    'errors': self.key_errors.get(key, 0),
                    'status': 'active' if self.key_errors.get(key, 0) < 5 else 'error'
                }
                for key in self.keys
            ]
        }
    
    def reset_errors(self, key: str) -> None:
        """Reset error count for a specific key."""
        if key in self.key_errors:
            self.key_errors[key] = 0
    
    def __len__(self) -> int:
        """Return the number of available API keys."""
        return len(self.keys)


# Global instance
api_key_manager = APIKeyManager()


def get_api_key() -> Optional[str]:
    """Convenience function to get an API key."""
    return api_key_manager.get_key()


def record_api_usage(key: str, success: bool = True) -> None:
    """Convenience function to record API usage."""
    api_key_manager.record_usage(key, success)


def get_api_usage_stats() -> Dict[str, Any]:
    """Convenience function to get API usage stats."""
    return api_key_manager.get_usage_stats()

