"""
FIFA Stats Platform - Configuration
====================================
Central configuration management using environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Base paths
BASE_DIR = Path(__file__).parent

# Store database in local AppData folder (NOT synced with OneDrive)
import os
LOCAL_DATA_DIR = Path(os.environ['LOCALAPPDATA']) / 'football_stats'
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_FOLDER = BASE_DIR / 'uploads'
DATABASE_PATH = LOCAL_DATA_DIR / 'fifa_stats.db'

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'fifa-stats-secret-key-2024-change-in-production')
DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

# Database Configuration
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_PATH}')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# File Upload Configuration
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5MB default
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_EXTENSIONS_SET = set(ext.strip() for ext in ALLOWED_EXTENSIONS)

# AI API Keys Configuration
def get_ai_api_keys():
    """
    Load AI API keys from environment variables.
    Supports both individual keys and comma-separated list.
    """
    keys = []
    
    # Check for comma-separated keys
    comma_keys = os.getenv('GEMINI_API_KEYS', '')
    if comma_keys:
        keys.extend([k.strip() for k in comma_keys.split(',') if k.strip()])
    
    # Check for individual keys
    for i in range(1, 5):
        key = os.getenv(f'GEMINI_API_KEY_{i}')
        if key:
            keys.append(key)
    
    return [k for k in keys if k]  # Filter out empty keys

# AI Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini')
AI_MODEL = os.getenv('AI_MODEL', 'gemini-1.5-flash')
AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', 3))
AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', 30))

# Scoring Configuration
SCORING_CONFIG = {
    'goals': 15,
    'assists': 10,
    'shots_on_target': 2,
    'possession_bonus': 5,
    'clean_sheet': 10,
    'pass_accuracy_bonus': 3,
    'tackles': 2,
    'max_score': 100
}

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache Configuration
CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
CACHE_DEFAULT_TIMEOUT = 300

# Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CORS
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Create upload folder if it doesn't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

