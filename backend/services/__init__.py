"""
FIFA Stats Platform - Services Package
=====================================
"""

from services.api_key_manager import api_key_manager, get_api_key, record_api_usage, get_api_usage_stats
from services.ai_analyzer import ai_analyzer, analyze_screenshot
from services.scoring import default_scorer, calculate_score, calculate_from_ai_result, get_scoring_config, update_scoring_config

__all__ = [
    'api_key_manager',
    'get_api_key',
    'record_api_usage',
    'get_api_usage_stats',
    'ai_analyzer',
    'analyze_screenshot',
    'default_scorer',
    'calculate_score',
    'calculate_from_ai_result',
    'get_scoring_config',
    'update_scoring_config'
]

