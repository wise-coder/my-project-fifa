"""
FIFA Stats Platform - User Routes
=================================
API routes for user dashboard functionality.
"""

import os
import uuid
import hashlib
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
user_bp = Blueprint('user', __name__)


def json_response(success=True, data=None, message='', status_code=200):
    """Create standardized JSON response."""
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code


def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
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


def get_upload_folder():
    """Get the upload folder path."""
    from flask import current_app
    return current_app.config.get('UPLOAD_FOLDER', 'uploads')


@user_bp.route('/upload', methods=['POST'])
def upload_screenshot():
    """
    Upload and process FIFA match screenshot.
    
    Expected form-data:
        - file: Image file (PNG/JPG)
        - competition_id: (optional) Competition ID
    
    Returns:
        JSON with match score and extracted stats
    """
    try:
        from flask_login import current_user
        from backend.database import db, Match
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        
        # Check if file is present
        if 'file' not in request.files:
            return json_response(False, message='No file provided', status_code=400)
        
        file = request.files['file']
        
        if file.filename == '':
            return json_response(False, message='No file selected', status_code=400)
        
        # Validate file type
        if not allowed_file(file.filename):
            return json_response(False, message='Invalid file type. Allowed: PNG, JPG, JPEG', status_code=400)
        
        # Get competition ID if provided
        competition_id = request.form.get('competition_id', type=int)
        
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = os.path.join(get_upload_folder(), filename)
        
        # Save file securely
        file.save(filepath)
        
        # Calculate image hash for duplicate detection
        image_hash = calculate_image_hash(filepath)
        
        if image_hash:
            # Check for duplicate submission
            existing_match = Match.query.filter_by(image_hash=image_hash).first()
            if existing_match:
                try:
                    os.remove(filepath)
                except:
                    pass
                return json_response(
                    False,
                    message='Duplicate screenshot detected! This image has already been uploaded.',
                    status_code=400
                )
        
        # Process image with AI to extract match statistics
        try:
            from services.ai_analyzer import analyze_screenshot
            from services.scoring import calculate_from_ai_result
            
            ai_result = analyze_screenshot(filepath)
            
            if not ai_result.get('success'):
                return json_response(
                    True,
                    data={
                        'match_id': None,
                        'message': 'File uploaded but AI processing failed',
                        'error': ai_result.get('error', 'Unknown error')
                    },
                    message='Upload partially successful'
                )
            
            # Check if screenshot contains valid match statistics
            if not ai_result.get('is_valid_screenshot', True):
                try:
                    os.remove(filepath)
                except:
                    pass
                
                return json_response(
                    False,
                    message='Screenshot does not contain valid match statistics. No points awarded.',
                    data={'score': 0},
                    status_code=400
                )
            
            # Calculate score from AI result
            score_result = calculate_from_ai_result(ai_result)
            match_score = score_result['total_score']
            
            # Extract stats
            stats = {
                'goals': ai_result.get('goals', 0),
                'assists': ai_result.get('assists', 0),
                'possession': ai_result.get('possession', 0),
                'shots': ai_result.get('shots', 0),
                'shots_on_target': ai_result.get('shots_on_target', 0),
                'pass_accuracy': ai_result.get('pass_accuracy', 0),
                'tackles': ai_result.get('tackles', 0)
            }
            
            # Save match to database
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
            
            # Update user's total score
            current_user.total_score += match_score
            
            # Create notification
            from database import create_notification
            create_notification(
                current_user.id,
                message=f'Congratulations! You scored {match_score} points 🎉 Goals: {stats["goals"]}, Possession: {stats["possession"]}%',
                title='Match Processed',
                notification_type='success'
            )
            
            db.session.commit()
            
            # Return success with the congratulatory message
            return json_response(
                True,
                data={
                    'match_id': match.id,
                    'match_score': match_score,
                    'stats': stats,
                    'score_breakdown': score_result.get('score_breakdown', {}),
                    'total_score': current_user.total_score,
                    'is_valid_screenshot': ai_result.get('is_valid_screenshot', True),
                    'is_fallback': ai_result.get('is_fallback', False)
                },
                message=f'Congratulations! You scored {match_score} points 🎉'
            )
            
        except Exception as ocr_error:
            logger.error(f"AI Processing Error: {ocr_error}")
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
        logger.error(f"Upload error: {e}")
        from backend.database import db
        db.session.rollback()
        return json_response(False, message='Upload failed', status_code=500)


@user_bp.route('/progress', methods=['GET'])
def get_progress():
    """
    Get user's progress statistics.
    
    Returns:
        JSON with user's progress data
    """
    try:
        from flask_login import current_user
        from backend.database import Match
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        
        # Get user's matches
        matches = Match.query.filter_by(user_id=current_user.id).order_by(Match.date_uploaded.desc()).all()
        
        matches_played = len(matches)
        total_points = current_user.total_score
        
        wins = sum(1 for m in matches if m.goals > 0)
        losses = matches_played - wins
        
        avg_score = sum(m.match_score for m in matches) / matches_played if matches_played > 0 else 0
        total_goals = sum(m.goals for m in matches)
        
        # Get recent matches
        recent_matches = [m.to_dict() for m in matches[:5]]
        
        # Get win rate
        win_rate = round((wins / matches_played) * 100) if matches_played > 0 else 0
        
        # Season progress (assuming 50 matches target)
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
                'total_goals': total_goals,
                'season_progress': season_progress
            },
            message='Progress retrieved successfully'
        )
        
    except Exception as e:
        logger.error(f"Progress error: {e}")
        return json_response(False, message='Failed to retrieve progress', status_code=500)


@user_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """
    Get user's notifications.
    
    Query Parameters:
        limit: Number of notifications to return (default: 20)
        unread_only: Only return unread notifications
    
    Returns:
        JSON with notifications list
    """
    try:
        from flask_login import current_user
        from backend.database import Notification
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        # Get notifications
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.date_created.desc()).limit(limit).all()
        
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


@user_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    """
    Mark a notification as read.
    
    Args:
        notification_id: ID of the notification to mark as read
        
    Returns:
        JSON success message
    """
    try:
        from flask_login import current_user
        from backend.database import Notification, db
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return json_response(False, message='Authentication required', status_code=401)
        
        # Find notification
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return json_response(False, message='Notification not found', status_code=404)
        
        # Mark as read
        notification.is_read = True
        db.session.commit()
        
        return json_response(True, message='Notification marked as read')
        
    except Exception as e:
        logger.error(f"Mark read error: {e}")
        return json_response(False, message='Failed to mark notification as read', status_code=500)


@user_bp.route('/user', methods=['GET'])
def get_user():
    """
    Get current user's profile.
    
    Returns:
        JSON with user data
    """
    try:
        from flask_login import current_user
        
        # Check if user is authenticated
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

