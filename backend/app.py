"""
FIFA Stats Platform - Main Flask Application
============================================
Backend API for FIFA Stats Platform with:
- User Authentication (Register, Login, Logout)
- Image/Screenshot Upload with OCR processing
- Scoring system
- Leaderboard
- User Progress
- Notifications

Run with: python app.py
"""

import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

# Import local modules
from database import db, User, Match, Notification, init_database, create_user, get_user_by_username, get_user_by_email, get_user_matches, get_user_notifications, create_notification
from ocr import process_screenshot
from scoring import default_scorer


# ============================================
# CONFIGURATION
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fifa-stats-secret-key-2024')

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "fifa_stats.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload configuration
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize extensions
db.init_app(app)
CORS(app, supports_credentials=True)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure Flask-Login to return JSON for unauthorized access
@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON response for unauthorized access instead of redirect."""
    return json_response(False, message='Authentication required', status_code=401)


# ============================================
# JWT/BEARER TOKEN AUTHENTICATION
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
    # Skip if user is already loaded via session
    if current_user.is_authenticated:
        return
    
    # Try to load from Bearer token
    token = get_token_auth_header()
    if token:
        # Use user_id from token (simple approach for demo)
        # In production, use proper JWT decode
        try:
            user_id = int(token)
            user = User.query.get(user_id)
            if user:
                login_user(user)
        except (ValueError, TypeError):
            pass

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================
# HELPER FUNCTIONS
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


def json_response(success=True, data=None, message='', status_code=200):
    """Create standardized JSON response."""
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code


def get_current_user_id():
    """Get current logged in user ID."""
    if current_user.is_authenticated:
        return current_user.id
    return None


# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Expected JSON:
    {
        "username": "string",
        "email": "string",
        "password": "string"
    }
    
    Returns:
        JSON with user data and success status
    """
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
            'Welcome to FIFA Stats! Start uploading your match screenshots to track your progress.'
        )
        
        return json_response(
            True,
            data={'user': user.to_dict()},
            message='Registration successful!',
            status_code=201
        )
        
    except Exception as e:
        print(f"Registration error: {e}")
        return json_response(False, message='Registration failed', status_code=500)


@app.route('/api/login', methods=['POST'])
def login():
    """
    Authenticate user and create session.
    
    Expected JSON:
    {
        "email": "string",
        "password": "string"
    }
    
    Returns:
        JSON with user data and token
    """
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return json_response(False, message='Email and password are required', status_code=400)
        
        # Find user by email
        user = get_user_by_email(email)
        
        if not user or not user.check_password(password):
            return json_response(False, message='Invalid email or password', status_code=401)
        
        # Login user
        login_user(user)
        
        # Create session data
        session['user_id'] = user.id
        session['username'] = user.username
        
        return json_response(
            True,
            data={
                'user': user.to_dict(),
                'token': str(user.id)  # Use user ID as Bearer token
            },
            message='Login successful!'
        )
    except Exception as e:
        print(f"Login error: {e}")
        return json_response(False, message='Login failed', status_code=500)


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout current user.
    
    Returns:
        JSON with success status
    """
    try:
        logout_user()
        session.clear()
        return json_response(True, message='Logout successful!')
    except Exception as e:
        print(f"Logout error: {e}")
        return json_response(False, message='Logout failed', status_code=500)


# ============================================
# UPLOAD ROUTES
# ============================================

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_screenshot():
    """
    Upload and process FIFA match screenshot.
    
    Expected form-data:
        - file: Image file (PNG/JPG)
    
    Returns:
        JSON with match score and extracted stats
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return json_response(False, message='No file provided', status_code=400)
        
        file = request.files['file']
        
        if file.filename == '':
            return json_response(False, message='No file selected', status_code=400)
        
        # Validate file type
        if not allowed_file(file.filename):
            return json_response(False, message='Invalid file type. Allowed: PNG, JPG, JPEG', status_code=400)
        
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(filepath)
        
        # Process image with OCR
        try:
            ocr_result = process_screenshot(filepath)
            
            if not ocr_result.get('success'):
                # OCR failed but file was saved
                return json_response(
                    True,
                    data={
                        'match_id': None,
                        'message': 'File uploaded but OCR processing failed',
                        'error': ocr_result.get('error', 'Unknown error')
                    },
                    message='Upload partially successful'
                )
            
            # Extract stats
            stats = {
                'goals': ocr_result.get('goals', 0),
                'possession': ocr_result.get('possession', 0),
                'shots_on_target': ocr_result.get('shots_on_target', 0),
                'pass_accuracy': ocr_result.get('pass_accuracy', 0),
                'tackles': ocr_result.get('tackles', 0)
            }
            
            # Calculate score
            score_result = default_scorer.calculate_score(stats)
            match_score = score_result['total_score']
            
            # Save match to database
            match = Match(
                user_id=current_user.id,
                image_filename=filename,
                match_score=match_score,
                goals=stats['goals'],
                possession=stats['possession'],
                shots_on_target=stats['shots_on_target'],
                pass_accuracy=stats['pass_accuracy'],
                tackles=stats['tackles']
            )
            db.session.add(match)
            
            # Update user's total score
            current_user.total_score += match_score
            
            # Create notification
            create_notification(
                current_user.id,
                f'Match uploaded! You scored {match_score} points. Goals: {stats["goals"]}, Possession: {stats["possession"]}%'
            )
            
            db.session.commit()
            
            return json_response(
                True,
                data={
                    'match_id': match.id,
                    'match_score': match_score,
                    'stats': stats,
                    'score_breakdown': score_result,
                    'total_score': current_user.total_score
                },
                message='Screenshot processed successfully!'
            )
            
        except Exception as ocr_error:
            print(f"OCR Error: {ocr_error}")
            # File was saved but OCR failed
            return json_response(
                True,
                data={
                    'match_id': None,
                    'message': 'File uploaded but processing failed',
                    'error': str(ocr_error)
                },
                message='Upload partially successful'
            )
        
    except Exception as e:
        print(f"Upload error: {e}")
        db.session.rollback()
        return json_response(False, message='Upload failed', status_code=500)


@app.route('/api/uploads/<filename>')
@login_required
def get_uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================
# LEADERBOARD ROUTES
# ============================================

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Get top players by total score.
    
    Query Parameters:
        limit: Number of players to return (default: 10)
    
    Returns:
        JSON with ranked list of players
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Get top users by total_score
        users = User.query.order_by(User.total_score.desc()).limit(limit).all()
        
        leaderboard = []
        for rank, user in enumerate(users, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'total_score': user.total_score
            })
        
        return json_response(
            True,
            data={'leaderboard': leaderboard},
            message='Leaderboard retrieved successfully'
        )
        
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return json_response(False, message='Failed to retrieve leaderboard', status_code=500)


# ============================================
# PROGRESS ROUTES
# ============================================

@app.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    """
    Get user's progress statistics.
    
    Returns:
        JSON with matches played, total points, recent scores
    """
    try:
        # Get all matches for current user
        matches = get_user_matches(current_user.id)
        
        # Calculate stats
        matches_played = len(matches)
        total_points = current_user.total_score
        
        wins = sum(1 for m in matches if m.goals > 0)  # Simplified win condition
        losses = matches_played - wins
        
        # Calculate average score
        avg_score = sum(m.match_score for m in matches) / matches_played if matches_played > 0 else 0
        
        # Calculate total goals
        total_goals = sum(m.goals for m in matches)
        
        # Calculate average stats
        avg_possession = sum(m.possession for m in matches) / matches_played if matches_played > 0 else 0
        avg_shots_on_target = sum(m.shots_on_target for m in matches) / matches_played if matches_played > 0 else 0
        avg_pass_accuracy = sum(m.pass_accuracy for m in matches) / matches_played if matches_played > 0 else 0
        avg_tackles = sum(m.tackles for m in matches) / matches_played if matches_played > 0 else 0
        
        # Get recent matches (last 5)
        recent_matches = [m.to_dict() for m in matches[:5]]
        
        # Get win rate
        win_rate = round((wins / matches_played) * 100) if matches_played > 0 else 0
        
        # Season progress based on matches (assuming 50 matches per season)
        season_matches_target = 50
        season_progress = min(round((matches_played / season_matches_target) * 100), 100)
        
        return json_response(
            True,
            data={
                'matches_played': matches_played,
                'wins': wins,
                'losses': losses,
                'total_points': total_points,
                'average_score': round(avg_score, 2),
                'win_rate': win_rate,
                'recent_matches': recent_matches,
                # New dynamic fields based on actual match data
                'total_goals': total_goals,
                'average_possession': round(avg_possession, 1),
                'average_shots_on_target': round(avg_shots_on_target, 1),
                'average_pass_accuracy': round(avg_pass_accuracy, 1),
                'average_tackles': round(avg_tackles, 1),
                'season_progress': season_progress,
                'season_matches_target': season_matches_target
            },
            message='Progress retrieved successfully'
        )
        
    except Exception as e:
        print(f"Progress error: {e}")
        return json_response(False, message='Failed to retrieve progress', status_code=500)


# ============================================
# NOTIFICATION ROUTES
# ============================================

@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """
    Get user's notifications.
    
    Query Parameters:
        limit: Number of notifications to return (default: 20)
        unread_only: Return only unread notifications (default: false)
    
    Returns:
        JSON with list of notifications
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        # Get notifications
        notifications = get_user_notifications(current_user.id, limit)
        
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        
        # Count unread
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
        print(f"Notifications error: {e}")
        return json_response(False, message='Failed to retrieve notifications', status_code=500)


@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
@login_required
def mark_notification_read(notification_id):
    """
    Mark a notification as read.
    
    Args:
        notification_id: ID of the notification
    
    Returns:
        JSON with success status
    """
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return json_response(False, message='Notification not found', status_code=404)
        
        notification.is_read = True
        db.session.commit()
        
        return json_response(
            True,
            message='Notification marked as read'
        )
        
    except Exception as e:
        print(f"Mark read error: {e}")
        return json_response(False, message='Failed to mark notification as read', status_code=500)


# ============================================
# USER ROUTES
# ============================================

@app.route('/api/user', methods=['GET'])
@login_required
def get_user():
    """
    Get current user's profile.
    
    Returns:
        JSON with user data
    """
    try:
        return json_response(
            True,
            data={'user': current_user.to_dict()},
            message='User data retrieved successfully'
        )
    except Exception as e:
        print(f"Get user error: {e}")
        return json_response(False, message='Failed to retrieve user data', status_code=500)


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return json_response(True, message='API is running')


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Initialize database
    with app.app_context():
        db.create_all()
        print("Database initialized!")
    
    # Run the app
    print("\n" + "="*50)
    print("FIFA Stats Platform API")
    print("="*50)
    print("Server running at: http://localhost:5000")
    print("API Endpoints:")
    print("  POST /api/register")
    print("  POST /api/login")
    print("  POST /api/logout")
    print("  POST /api/upload")
    print("  GET  /api/leaderboard")
    print("  GET  /api/progress")
    print("  GET  /api/notifications")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
