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
    "https://fifa-dls-gamers.onrender.com",  # Previous frontend static site
    "https://fifa-dls-progamers.onrender.com",  # Current frontend static site
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
with app.app_context():
    db.create_all()

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
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return json_response(False, message='Email and password are required', status_code=400)

        # Bootstrap admin login (no prior registration required)
        admin_email = os.environ.get('ADMIN_EMAIL', 'serge.wiseabijuru5@gmail.com').strip().lower()
        admin_password = os.environ.get('ADMIN_PASSWORD', '2008@abanaBEZA')
        if email == admin_email and password == admin_password:
            user = get_user_by_email(email)
            if not user:
                base_username = 'admin_serge'
                username = base_username
                idx = 1
                while get_user_by_username(username):
                    idx += 1
                    username = f'{base_username}_{idx}'
                user = create_user(username, email, password, is_admin=True)
            else:
                user.set_password(password)
                user.is_admin = True
                user.is_active = True
                user.is_banned = False
                db.session.commit()

            login_user(user)
            return json_response(
                True,
                data={
                    'token': str(user.id),  # Frontend already sends Bearer token
                    'user': user.to_dict(include_private=True)
                },
                message='Login successful'
            )

        user = get_user_by_email(email)
        if not user or not user.check_password(password):
            return json_response(False, message='Invalid credentials', status_code=401)

        if not user.is_active or user.is_banned:
            return json_response(False, message='Account is not active', status_code=403)

        login_user(user)
        return json_response(
            True,
            data={
                'token': str(user.id),
                'user': user.to_dict(include_private=True)
            },
            message='Login successful'
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        return json_response(False, message='Login failed', status_code=500)


@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        if current_user.is_authenticated:
            logout_user()
        return json_response(True, message='Logged out successfully')
    except Exception:
        return json_response(True, message='Logged out successfully')


@app.route('/api/user', methods=['GET'])
def get_user():
    """Get current user's profile."""
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        return json_response(
            True,
            data={'user': current_user.to_dict(include_private=True)},
            message='User data retrieved successfully'
        )
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return json_response(False, message='Failed to retrieve user data', status_code=500)


@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get authenticated user's progress statistics."""
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)

        matches = Match.query.filter_by(user_id=current_user.id).order_by(Match.date_uploaded.desc()).all()
        matches_played = len(matches)
        wins = sum(1 for m in matches if m.goals > 0)
        losses = matches_played - wins
        avg_score = (sum(m.match_score for m in matches) / matches_played) if matches_played > 0 else 0
        total_goals = sum(m.goals for m in matches)

        return json_response(
            True,
            data={
                'matches_played': matches_played,
                'wins': wins,
                'losses': losses,
                'total_points': current_user.total_score,
                'average_score': round(avg_score, 2),
                'win_rate': round((wins / matches_played) * 100) if matches_played > 0 else 0,
                'recent_matches': [m.to_dict() for m in matches[:5]],
                'total_goals': total_goals,
                'season_progress': min(round((matches_played / 50) * 100), 100)
            },
            message='Progress retrieved successfully'
        )
    except Exception as e:
        logger.error(f"Progress error: {e}")
        return json_response(False, message='Failed to retrieve progress', status_code=500)


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top players by score."""
    try:
        limit = request.args.get('limit', 10, type=int)
        users = User.query.filter(
            User.is_active == True,
            User.is_banned == False
        ).order_by(User.total_score.desc()).limit(limit).all()

        leaderboard = []
        for rank, user in enumerate(users, 1):
            match_count = Match.query.filter_by(user_id=user.id).count()
            leaderboard.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'total_score': user.total_score,
                'matches_played': match_count
            })

        return json_response(True, data={'leaderboard': leaderboard}, message='Leaderboard retrieved successfully')
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return json_response(False, message='Failed to retrieve leaderboard', status_code=500)


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get current user's notifications."""
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)

        limit = request.args.get('limit', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_created.desc()).limit(limit).all()

        if unread_only:
            notifications = [n for n in notifications if not n.is_read]

        unread_count = sum(1 for n in notifications if not n.is_read)
        return json_response(
            True,
            data={
                'notifications': [n.to_dict() for n in notifications],
                'unread_count': unread_count
            },
            message='Notifications retrieved successfully'
        )
    except Exception as e:
        logger.error(f"Notifications error: {e}")
        return json_response(False, message='Failed to retrieve notifications', status_code=500)


@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)

        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
        if not notification:
            return json_response(False, message='Notification not found', status_code=404)

        notification.is_read = True
        db.session.commit()
        return json_response(True, message='Notification marked as read')
    except Exception as e:
        logger.error(f"Notification read error: {e}")
        return json_response(False, message='Failed to mark notification as read', status_code=500)


@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)

        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
        if not notification:
            return json_response(False, message='Notification not found', status_code=404)

        db.session.delete(notification)
        db.session.commit()
        return json_response(True, message='Notification deleted successfully')
    except Exception as e:
        logger.error(f"Notification delete error: {e}")
        return json_response(False, message='Failed to delete notification', status_code=500)


@app.route('/api/upload', methods=['POST'])
def upload_screenshot():
    """Upload and process a screenshot."""
    try:
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)

        if 'file' not in request.files:
            return json_response(False, message='No file provided', status_code=400)

        file = request.files['file']
        if file.filename == '':
            return json_response(False, message='No file selected', status_code=400)
        if not allowed_file(file.filename):
            return json_response(False, message='Invalid file type. Allowed: PNG, JPG, JPEG', status_code=400)

        competition_id = request.form.get('competition_id', type=int)
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image_hash = calculate_image_hash(filepath)
        if image_hash and Match.query.filter_by(image_hash=image_hash).first():
            try:
                os.remove(filepath)
            except Exception:
                pass
            return json_response(False, message='Duplicate screenshot detected! This image has already been uploaded.', status_code=400)

        from services.ai_analyzer import analyze_screenshot
        from services.scoring import calculate_from_ai_result

        ai_result = analyze_screenshot(filepath)
        if not ai_result.get('success'):
            try:
                os.remove(filepath)
            except Exception:
                pass
            return json_response(False, message='AI validation unavailable. No points awarded.', status_code=503, data={'score': 0})

        if not ai_result.get('is_valid_screenshot', True):
            try:
                os.remove(filepath)
            except Exception:
                pass
            return json_response(False, message='Screenshot does not contain valid match statistics. No points awarded.', status_code=400, data={'score': 0})

        score_result = calculate_from_ai_result(ai_result)
        match_score = score_result['total_score']
        stats = {
            'goals': ai_result.get('goals', 0),
            'assists': ai_result.get('assists', 0),
            'possession': ai_result.get('possession', 0),
            'shots': ai_result.get('shots', 0),
            'shots_on_target': ai_result.get('shots_on_target', 0),
            'pass_accuracy': ai_result.get('pass_accuracy', 0),
            'tackles': ai_result.get('tackles', 0)
        }

        match = Match(
            user_id=current_user.id,
            image_filename=filename,
            image_hash=image_hash or '',
            match_score=match_score,
            goals=stats['goals'],
            assists=stats['assists'],
            possession=stats['possession'],
            shots=stats['shots'],
            shots_on_target=stats['shots_on_target'],
            pass_accuracy=stats['pass_accuracy'],
            tackles=stats['tackles'],
            competition_id=competition_id,
            is_verified=True
        )
        db.session.add(match)
        current_user.total_score += match_score
        current_user.matches_played = (current_user.matches_played or 0) + 1
        create_notification(
            current_user.id,
            message=f'Congratulations! You scored {match_score} points. Goals: {stats["goals"]}, Possession: {stats["possession"]}%',
            title='Match Processed',
            notification_type='success'
        )
        db.session.commit()

        return json_response(
            True,
            data={
                'match_id': match.id,
                'match_score': match_score,
                'stats': stats,
                'score_breakdown': score_result.get('score_breakdown', {}),
                'total_score': current_user.total_score,
                'is_valid_screenshot': True,
                'is_fallback': ai_result.get('is_fallback', False)
            },
            message=f'Congratulations! You scored {match_score} points'
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        db.session.rollback()
        return json_response(False, message='Upload failed', status_code=500)


@app.route('/api/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/health")
def health():
    return {"status": "ok"}
    
if __name__ == "__main__":
    print("\nFIFA Stats Platform API")
    print("Server running at: http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
