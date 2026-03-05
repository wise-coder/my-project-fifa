"""
FIFA Stats Platform - Leaderboard Routes
=====================================
API routes for leaderboard functionality.
"""

import logging
from flask import Blueprint, request, jsonify

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
leaderboard_bp = Blueprint('leaderboard', __name__)


def json_response(success=True, data=None, message='', status_code=200):
    """Create standardized JSON response."""
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code


@leaderboard_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Get top players by total score.
    
    Query Parameters:
        limit: Number of players to return (default: 10)
    
    Returns:
        JSON with ranked list of players
    """
    try:
        from backend.database import User
        
        # Get limit parameter
        limit = request.args.get('limit', 10, type=int)
        
        # Get top users by total_score, excluding banned users
        users = User.query.filter(
            User.is_active == True,
            User.is_banned == False
        ).order_by(User.total_score.desc()).limit(limit).all()
        
        # Build leaderboard with ranks
        leaderboard = []
        for rank, user in enumerate(users, 1):
            # Get match count for this user
            from backend.database import Match
            match_count = Match.query.filter_by(user_id=user.id).count()
            
            leaderboard.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'total_score': user.total_score,
                'matches_played': match_count
            })
        
        return json_response(
            True,
            data={'leaderboard': leaderboard},
            message='Leaderboard retrieved successfully'
        )
        
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return json_response(False, message='Failed to retrieve leaderboard', status_code=500)


@leaderboard_bp.route('/leaderboard/<int:user_id>', methods=['GET'])
def get_user_rank(user_id):
    """
    Get a specific user's rank.
    
    Args:
        user_id: ID of the user
        
    Returns:
        JSON with user's rank information
    """
    try:
        from backend.database import User, Match
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return json_response(False, message='User not found', status_code=404)
        
        # Calculate rank
        higher_score_count = User.query.filter(
            User.total_score > user.total_score,
            User.is_active == True,
            User.is_banned == False
        ).count()
        
        rank = higher_score_count + 1
        
        # Get match count
        match_count = Match.query.filter_by(user_id=user_id).count()
        
        # Get total players
        total_players = User.query.filter(
            User.is_active == True,
            User.is_banned == False
        ).count()
        
        return json_response(
            True,
            data={
                'user_id': user_id,
                'username': user.username,
                'rank': rank,
                'total_score': user.total_score,
                'matches_played': match_count,
                'total_players': total_players
            },
            message='User rank retrieved successfully'
        )
        
    except Exception as e:
        logger.error(f"Get user rank error: {e}")
        return json_response(False, message='Failed to retrieve user rank', status_code=500)

