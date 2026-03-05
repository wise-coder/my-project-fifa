"""
FIFA Stats Platform - Routes Package
==================================
"""

from routes.user_routes import user_bp
from routes.leaderboard_routes import leaderboard_bp

__all__ = ['user_bp', 'leaderboard_bp']

