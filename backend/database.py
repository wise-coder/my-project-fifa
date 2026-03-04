"""
FIFA Stats Platform - Database Models
=====================================
SQLite database models using SQLAlchemy ORM.
"""

import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model for authentication and tracking total score.
    
    Fields:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Hashed password
        total_score: Cumulative score from all matches
        created_at: Account creation timestamp
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    matches = db.relationship('Match', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary for JSON response."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'total_score': self.total_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class Match(db.Model):
    """
    Match model for storing uploaded match results.
    
    Fields:
        id: Primary key
        user_id: Foreign key to User
        image_filename: Name of uploaded image file
        match_score: Points earned from this match
        goals: Goals scored (from OCR)
        possession: Possession percentage (from OCR)
        shots_on_target: Shots on target (from OCR)
        pass_accuracy: Pass accuracy percentage (from OCR)
        tackles: Tackles won (from OCR)
        date_uploaded: Timestamp of upload
    """
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_filename = db.Column(db.String(256), nullable=False)
    match_score = db.Column(db.Integer, default=0)
    
    # OCR Extracted Stats
    goals = db.Column(db.Integer, default=0)
    possession = db.Column(db.Integer, default=0)
    shots_on_target = db.Column(db.Integer, default=0)
    pass_accuracy = db.Column(db.Integer, default=0)
    tackles = db.Column(db.Integer, default=0)
    
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert match to dictionary for JSON response."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_filename': self.image_filename,
            'match_score': self.match_score,
            'goals': self.goals,
            'possession': self.possession,
            'shots_on_target': self.shots_on_target,
            'pass_accuracy': self.pass_accuracy,
            'tackles': self.tackles,
            'date_uploaded': self.date_uploaded.isoformat() if self.date_uploaded else None
        }
    
    def __repr__(self):
        return f'<Match {self.id} for User {self.user_id}>'


class Notification(db.Model):
    """
    Notification model for user notifications.
    
    Fields:
        id: Primary key
        user_id: Foreign key to User
        message: Notification message
        is_read: Read status
        date: Timestamp
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert notification to dictionary for JSON response."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'is_read': self.is_read,
            'date': self.date.isoformat() if self.date else None
        }
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'


def init_database(app):
    """
    Initialize the database with the app context.
    Creates all tables if they don't exist.
    """
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")


def get_user_by_id(user_id):
    """Get user by ID."""
    return User.query.get(user_id)


def get_user_by_username(username):
    """Get user by username."""
    return User.query.filter_by(username=username).first()


def get_user_by_email(email):
    """Get user by email."""
    return User.query.filter_by(email=email).first()


def create_user(username, email, password):
    """Create a new user."""
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def get_user_matches(user_id, limit=None):
    """Get matches for a user."""
    query = Match.query.filter_by(user_id=user_id).order_by(Match.date_uploaded.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_user_notifications(user_id, limit=None):
    """Get notifications for a user."""
    query = Notification.query.filter_by(user_id=user_id).order_by(Notification.date.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def create_notification(user_id, message):
    """Create a notification for a user."""
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()
    return notification
