"""
FIFA Stats Platform - Main Flask Application
============================================
Production-ready backend API for FIFA Stats Platform with:
- User Authentication (Register, Login, Logout)
- Screenshot Upload with AI processing
- Multiple Gemini API key support
- Duplicate detection
- Admin Panel APIs
- Leaderboard
- Notifications

CORS Configuration for frontend at http://127.0.0.1:5501

Run with: python app.py
"""

import os
import uuid
import hashlib
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ============================================
# CORS CONFIGURATION
# ============================================

# Define allowed origins
# In production, replace with your actual frontend URL
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5501",  # Live Server
    "http://localhost:5501",   # Localhost variant
    "http://127.0.0.1:5000",  # Same origin fallback
    "http://localhost:5000",   # Same origin fallback
    "https://fifa-dls-gamers.onrender.com",  # Frontend static site
    "https://fifa-fighters.onrender.com",    # Backend / same-site calls
]

def create_cors_config():
    """
    Create CORS configuration dictionary.
    This ensures credentials work properly with allowed origins.
    """
    return {
        'origins': ALLOWED_ORIGINS,
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
        'supports_credentials': True,  # Critical for credentials: include
        'expose_headers': ['Content-Length', 'Content-Type'],
        'max_age': 3600  # Cache preflight for 1 hour
    }


# ============================================
# CONFIGURATION
# ============================================

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fifa-stats-secret-key-2024')

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "fifa_stats.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload configuration
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5MB default
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# ============================================
# INITIALIZE CORS WITH CREDENTIALS
# ============================================

# Initialize CORS with explicit configuration for credentials
# This is the key fix for the CORS error
cors_config = create_cors_config()
CORS(app, 
     origins=cors_config['origins'],
     methods=cors_config['methods'],
     allow_headers=cors_config['allow_headers'],
     supports_credentials=cors_config['supports_credentials'],  # MUST be True
     expose_headers=cors_config['expose_headers'],
     max_age=cors_config['max_age']
)

# ============================================
# INITIALIZE DATABASE AND LOGIN
# ============================================

# Import database after app creation to avoid circular imports
from database import db, User, Match, Notification, Competition, init_database
from database import (
    create_user, get_user_by_username, get_user_by_email, 
    get_user_matches, get_user_notifications, create_notification,
    is_duplicate_image, store_image_hash, get_all_users, get_all_matches,
    get_all_competitions, create_competition, update_competition,
    get_leaderboard as db_get_leaderboard, get_user_count, get_active_user_count, 
    get_banned_user_count, get_match_count, get_pending_match_count,
    create_system_notification, get_all_users as db_get_all_users, get_all_matches as db_get_all_matches
)

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure Flask-Login for JSON responses
@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON response for unauthorized access."""
    return json_response(False, message='Authentication required', status_code=401)

# ============================================
# AUTHENTICATION HELPERS
# ============================================

def get_token_auth_header():
    """Get Bearer token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None


@app.before_request
def load_user_from_token():
    """Load user from Bearer token if session is not available."""
    if current_user.is_authenticated:
        return
    
    token = get_token_auth_header()
    if token:
        try:
            user_id = int(token)
            user = User.query.get(user_id)
            if user and user.is_active and not user.is_banned:
                login_user(user)
        except (ValueError, TypeError):
            pass


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        if not current_user.is_admin:
            return json_response(False, message='Admin privileges required', status_code=403)
        return f(*args, **kwargs)
    return decorated_function


# Create upload folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================
# HELPER FUNCTIONS
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_image_hash(filepath):
    """Calculate SHA256 hash of image file for duplicate detection."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating image hash: {e}")
        return None


def json_response(success=True, data=None, message='', status_code=200):
    """Create standardized JSON response."""
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code


# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    """
    Register a new user.
    
    Expected JSON:
    {
        "username": "string",
        "email": "string",
        "password": "string"
    }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return json_response(False, message=f'{field} is required', status_code=400)
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # Validate username length
        if len(username) < 3:
            return json_response(False, message='Username must be at least 3 characters', status_code=400)
        
        # Validate password length
        if len(password) < 6:
            return json_response(False, message='Password must be at least 6 characters', status_code=400)
        
        # Check if username already exists
        if get_user_by_username(username):
            return json_response(False, message='Username already exists', status_code=400)
        
        # Check if email already exists
        if get_user_by_email(email):
            return json_response(False, message='Email already exists', status_code=400)
        
        # Create new user
        user = create_user(username, email, password)
        
        # Create welcome notification
        create_notification(
            user.id,
            message='Welcome to FIFA Stats! Start uploading your match screenshots to track your progress.',
            title='Welcome!'
        )
        
        return json_response(
            True,
            data={'user': user.to_dict()},
            message='Registration successful!',
            status_code=201
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return json_response(False, message='Registration failed', status_code=500)


@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """
    Authenticate user and create session.
    """
@app.route("/health")
def health():
    return {"status": "ok"}
    
if __name__ == "__main__":
    print("\nFIFA Stats Platform API")
    print("Server running at: http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
