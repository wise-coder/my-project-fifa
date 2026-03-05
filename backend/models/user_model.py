"""
FIFA Stats Platform - User Model
================================
SQLAlchemy model for Users table.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User:
    """
    User model for the FIFA Stats platform.
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Hashed password
        total_score: Accumulated points from matches
        matches_played: Number of matches uploaded
        rank: Current leaderboard rank (computed)
        is_active: Account active status
        is_admin: Admin privileges flag
        is_banned: Ban status flag
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        id: int = None,
        username: str = None,
        email: str = None,
        password_hash: str = None,
        total_score: int = 0,
        matches_played: int = 0,
        is_active: bool = True,
        is_admin: bool = False,
        is_banned: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.total_score = total_score
        self.matches_played = matches_played
        self.is_active = is_active
        self.is_admin = is_admin
        self.is_banned = is_banned
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def set_password(self, password: str) -> None:
        """Set hashed password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_private: bool = False) -> dict:
        """
        Convert user to dictionary.
        
        Args:
            include_private: Include sensitive fields
            
        Returns:
            Dict representation of user
        """
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_private else None,
            'total_score': self.total_score,
            'matches_played': self.matches_played,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_banned': self.is_banned,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    def __repr__(self) -> str:
        return f'<User {self.username}>'


def create_user(username: str, email: str, password: str, is_admin: bool = False) -> User:
    """
    Create a new user.
    
    Args:
        username: Unique username
        email: Unique email address
        password: Plain text password
        is_admin: Admin flag
        
    Returns:
        Created User instance
    """
    from backend.database import db
    
    user = User(
        username=username,
        email=email.lower(),
        is_admin=is_admin
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return user


def get_user_by_username(username: str) -> User:
    """Get user by username."""
    from backend.database import db, User as UserModel
    return UserModel.query.filter_by(username=username).first()


def get_user_by_email(email: str) -> User:
    """Get user by email."""
    from backend.database import db, User as UserModel
    return UserModel.query.filter_by(email=email.lower()).first()


def get_user_by_id(user_id: int) -> User:
    """Get user by ID."""
    from backend.database import db, User as UserModel
    return UserModel.query.get(user_id)

