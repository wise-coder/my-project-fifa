"""
FIFA Stats Platform - Match Model
=================================
SQLAlchemy model for Matches table.
"""

from datetime import datetime


class Match:
    """
    Match model for the FIFA Stats platform.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        image_filename: Stored screenshot filename
        image_hash: SHA256 hash for duplicate detection
        match_score: Points earned from this match
        goals: Goals scored
        assists: Assists made
        possession: Possession percentage
        shots: Total shots
        shots_on_target: Shots on target
        pass_accuracy: Pass accuracy percentage
        tackles: Successful tackles
        competition_id: Optional competition foreign key
        is_verified: Verification status
        rejection_reason: Reason if rejected
        date_uploaded: Upload timestamp
    """
    
    def __init__(
        self,
        id: int = None,
        user_id: int = None,
        image_filename: str = None,
        image_hash: str = None,
        match_score: int = 0,
        goals: int = 0,
        assists: int = 0,
        possession: int = 0,
        shots: int = 0,
        shots_on_target: int = 0,
        pass_accuracy: int = 0,
        tackles: int = 0,
        competition_id: int = None,
        is_verified: bool = False,
        rejection_reason: str = None,
        date_uploaded: datetime = None
    ):
        self.id = id
        self.user_id = user_id
        self.image_filename = image_filename
        self.image_hash = image_hash
        self.match_score = match_score
        self.goals = goals
        self.assists = assists
        self.possession = possession
        self.shots = shots
        self.shots_on_target = shots_on_target
        self.pass_accuracy = pass_accuracy
        self.tackles = tackles
        self.competition_id = competition_id
        self.is_verified = is_verified
        self.rejection_reason = rejection_reason
        self.date_uploaded = date_uploaded or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """
        Convert match to dictionary.
        
        Returns:
            Dict representation of match
        """
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
    
    def __repr__(self) -> str:
        return f'<Match {self.id} User:{self.user_id} Score:{self.match_score}>'


def create_match(
    user_id: int,
    image_filename: str,
    match_score: int,
    goals: int = 0,
    assists: int = 0,
    possession: int = 0,
    shots: int = 0,
    shots_on_target: int = 0,
    pass_accuracy: int = 0,
    tackles: int = 0,
    image_hash: str = None,
    competition_id: int = None
) -> Match:
    """
    Create a new match record.
    
    Args:
        user_id: User who uploaded the match
        image_filename: Saved screenshot filename
        match_score: Calculated score
        goals: Goals scored
        assists: Assists made
        possession: Possession percentage
        shots: Total shots
        shots_on_target: Shots on target
        pass_accuracy: Pass accuracy percentage
        tackles: Successful tackles
        image_hash: SHA256 hash for duplicate detection
        competition_id: Optional competition ID
        
    Returns:
        Created Match instance
    """
    from backend.database import db
    
    match = Match(
        user_id=user_id,
        image_filename=image_filename,
        image_hash=image_hash,
        match_score=match_score,
        goals=goals,
        assists=assists,
        possession=possession,
        shots=shots,
        shots_on_target=shots_on_target,
        pass_accuracy=pass_accuracy,
        tackles=tackles,
        competition_id=competition_id,
        is_verified=True
    )
    
    db.session.add(match)
    db.session.commit()
    
    return match


def get_user_matches(user_id: int, limit: int = None) -> list:
    """
    Get all matches for a user.
    
    Args:
        user_id: User ID
        limit: Optional limit for number of matches
        
    Returns:
        List of Match instances
    """
    from backend.database import db, Match as MatchModel
    
    query = MatchModel.query.filter_by(user_id=user_id).order_by(MatchModel.date_uploaded.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_match_by_id(match_id: int) -> Match:
    """Get match by ID."""
    from backend.database import db, Match as MatchModel
    return MatchModel.query.get(match_id)


def get_all_matches(filters: dict = None) -> list:
    """
    Get all matches with optional filters.
    
    Args:
        filters: Optional filter dictionary
        
    Returns:
        List of Match instances
    """
    from backend.database import db, Match as MatchModel
    
    query = MatchModel.query
    
    if filters:
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])
        if 'competition_id' in filters:
            query = query.filter_by(competition_id=filters['competition_id'])
        if 'status' in filters:
            if filters['status'] == 'verified':
                query = query.filter_by(is_verified=True)
            elif filters['status'] == 'pending':
                query = query.filter_by(is_verified=False)
    
    return query.order_by(MatchModel.date_uploaded.desc()).all()

