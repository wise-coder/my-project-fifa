"""
FIFA Stats Platform - Database Module
====================================
SQLAlchemy database configuration and models.
"""

import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()


# ============================================
# USER MODEL
# ============================================

class User(db.Model):
    """User model for authentication and tracking."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = db.relationship('Match', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_private=False):
        """Convert user to dictionary."""
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
        return {k: v for k, v in data.items() if v is not None}
    
    def __repr__(self):
        return f'<User {self.username}>'


# ============================================
# MATCH MODEL
# ============================================

class Match(db.Model):
    """Match model for storing uploaded match statistics."""
    
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_filename = db.Column(db.String(256))
    image_hash = db.Column(db.String(64))  # For duplicate detection
    match_score = db.Column(db.Integer, default=0)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    possession = db.Column(db.Integer, default=0)
    shots = db.Column(db.Integer, default=0)
    shots_on_target = db.Column(db.Integer, default=0)
    pass_accuracy = db.Column(db.Integer, default=0)
    tackles = db.Column(db.Integer, default=0)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'))
    is_verified = db.Column(db.Boolean, default=False)
    rejection_reason = db.Column(db.Text)
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert match to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_filename': self.image_filename,
            'match_score': self.match_score,
            'goals': self.goals,
            'assists': self.assists,
            'possession': self.possession,
            'shots': self.shots,
            'shots_on_target': self.shots_on_target,
            'pass_accuracy': self.pass_accuracy,
            'tackles': self.tackles,
            'competition_id': self.competition_id,
            'is_verified': self.is_verified,
            'rejection_reason': self.rejection_reason,
            'date_uploaded': self.date_uploaded.isoformat() if self.date_uploaded else None
        }
    
    def __repr__(self):
        return f'<Match {self.id} User:{self.user_id} Score:{self.match_score}>'


# ============================================
# NOTIFICATION MODEL
# ============================================

class Notification(db.Model):
    """Notification model for user alerts."""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(128))
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(32), default='info')  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert notification to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'date': self.date_created.isoformat() if self.date_created else None
        }
    
    def __repr__(self):
        return f'<Notification {self.id} User:{self.user_id}>'


# ============================================
# COMPETITION MODEL
# ============================================

class Competition(db.Model):
    """Competition model for tournaments."""
    
    __tablename__ = 'competitions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(32), default='upcoming')  # upcoming, active, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    matches = db.relationship('Match', backref='competition', lazy=True)
    
    def to_dict(self):
        """Convert competition to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Competition {self.name}>'


# ============================================
# HELPER FUNCTIONS
# ============================================

def init_database(app):
    """Initialize database with Flask app."""
    db.init_app(app)


def create_user(username, email, password, is_admin=False):
    """Create a new user."""
    user = User(
        username=username,
        email=email.lower(),
        is_admin=is_admin
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def get_user_by_username(username):
    """Get user by username."""
    return User.query.filter_by(username=username).first()


def get_user_by_email(email):
    """Get user by email."""
    return User.query.filter_by(email=email.lower()).first()


def get_user_by_id(user_id):
    """Get user by ID."""
    return User.query.get(user_id)


def get_all_users(filters=None):
    """Get all users with optional filters."""
    query = User.query
    
    if filters:
        if filters.get('status') == 'active':
            query = query.filter_by(is_active=True, is_banned=False)
        elif filters.get('status') == 'inactive':
            query = query.filter_by(is_active=False)
        elif filters.get('status') == 'banned':
            query = query.filter_by(is_banned=True)
        
        if filters.get('search'):
            search = f"%{filters['search']}%"
            query = query.filter(
                (User.username.like(search)) | 
                (User.email.like(search))
            )
    
    return query.order_by(User.total_score.desc()).all()


def get_user_count():
    """Get total user count."""
    return User.query.count()


def get_active_user_count():
    """Get active user count."""
    return User.query.filter_by(is_active=True, is_banned=False).count()


def get_banned_user_count():
    """Get banned user count."""
    return User.query.filter_by(is_banned=True).count()


def get_user_matches(user_id, limit=None):
    """Get all matches for a user."""
    query = Match.query.filter_by(user_id=user_id).order_by(Match.date_uploaded.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_all_matches(filters=None):
    """Get all matches with optional filters."""
    query = Match.query
    
    if filters:
        if filters.get('user_id'):
            query = query.filter_by(user_id=filters['user_id'])
        if filters.get('competition_id'):
            query = query.filter_by(competition_id=filters['competition_id'])
        if filters.get('status') == 'verified':
            query = query.filter_by(is_verified=True)
        elif filters.get('status') == 'pending':
            query = query.filter_by(is_verified=False)
    
    return query.order_by(Match.date_uploaded.desc()).all()


def get_match_count():
    """Get total match count."""
    return Match.query.count()


def get_pending_match_count():
    """Get pending match count."""
    return Match.query.filter_by(is_verified=False).count()


def get_leaderboard(limit=10):
    """Get leaderboard (top users by score)."""
    return User.query.filter(
        User.is_active == True,
        User.is_banned == False
    ).order_by(User.total_score.desc()).limit(limit).all()


def create_notification(user_id, message, title=None, notification_type='info'):
    """Create a notification for a user."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def get_user_notifications(user_id, limit=20):
    """Get notifications for a user."""
    return Notification.query.filter_by(
        user_id=user_id
    ).order_by(Notification.date_created.desc()).limit(limit).all()


def is_duplicate_image(image_hash):
    """Check if image hash already exists."""
    return Match.query.filter_by(image_hash=image_hash).first() is not None


def store_image_hash(image_hash, user_id, match_id):
    """Store image hash is already handled in Match creation."""
    pass  # Hash is stored in Match.image_hash


def get_all_competitions():
    """Get all competitions."""
    return Competition.query.order_by(Competition.created_at.desc()).all()


def create_competition(name, description='', start_date=None, end_date=None):
    """Create a new competition."""
    competition = Competition(
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date
    )
    db.session.add(competition)
    db.session.commit()
    return competition


def update_competition(competition_id, **kwargs):
    """Update a competition."""
    competition = Competition.query.get(competition_id)
    if not competition:
        return None
    
    for key, value in kwargs.items():
        if hasattr(competition, key):
            setattr(competition, key, value)
    
    db.session.commit()
    return competition


def create_system_notification(message, title='System'):
    """Create notification for all admins."""
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        create_notification(admin.id, message, title, 'info')

