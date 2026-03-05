"""
FIFA Stats Platform - Scoring Service
====================================
Calculates player scores based on match statistics.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Default scoring configuration
DEFAULT_SCORING = {
    'goals': 15,              # Points per goal
    'assists': 10,            # Points per assist
    'shots_on_target': 2,     # Points per shot on target
    'possession_bonus': 5,    # Bonus for possession over 50%
    'clean_sheet': 10,        # Bonus for clean sheet (0 goals conceded)
    'pass_accuracy_bonus': 3, # Bonus for pass accuracy over 80%
    'tackles': 2,             # Points per successful tackle
    'win_bonus': 20,          # Bonus for winning
    'max_score': 100          # Maximum possible score
}


class ScoringService:
    """
    Calculates player scores based on match performance statistics.
    
    Scoring Rules:
    - Goals: 15 points each
    - Assists: 10 points each
    - Shots on Target: 2 points each
    - Possession Bonus: 5 points if possession > 50%
    - Clean Sheet: 10 points if opponent scored 0
    - Pass Accuracy Bonus: 3 points if pass accuracy > 80%
    - Tackles: 2 points each
    - Win Bonus: 20 points
    
    Total score is normalized to 0-100 range.
    """
    
    def __init__(self, config: Dict[str, int] = None):
        """
        Initialize the scoring service with optional custom config.
        
        Args:
            config: Optional custom scoring configuration
        """
        self.config = config or DEFAULT_SCORING.copy()
        logger.info(f"Scoring Service initialized with config: {self.config}")
    
    def calculate_score(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the player score based on match statistics.
        
        Args:
            stats: Dict containing match statistics
                - goals: int
                - assists: int
                - possession: int (0-100)
                - shots_on_target: int
                - pass_accuracy: int (0-100)
                - tackles: int
                - goals_conceded: int (optional)
                - is_win: bool (optional)
                
        Returns:
            Dict containing:
                - total_score: int (0-100)
                - score_breakdown: dict showing points from each category
                - max_possible: int
        """
        score_breakdown = {}
        total_points = 0
        
        # Goals scoring
        goals = stats.get('goals', 0)
        goals_points = goals * self.config['goals']
        score_breakdown['goals'] = goals_points
        total_points += goals_points
        
        # Assists
        assists = stats.get('assists', 0)
        assists_points = assists * self.config['assists']
        score_breakdown['assists'] = assists_points
        total_points += assists_points
        
        # Shots on target
        shots_on_target = stats.get('shots_on_target', 0)
        sot_points = shots_on_target * self.config['shots_on_target']
        score_breakdown['shots_on_target'] = sot_points
        total_points += sot_points
        
        # Tackles
        tackles = stats.get('tackles', 0)
        tackles_points = tackles * self.config['tackles']
        score_breakdown['tackles'] = tackles_points
        total_points += tackles_points
        
        # Possession bonus (if > 50%)
        possession = stats.get('possession', 0)
        if possession > 50:
            possession_bonus = self.config['possession_bonus']
            score_breakdown['possession_bonus'] = possession_bonus
            total_points += possession_bonus
        
        # Pass accuracy bonus (if > 80%)
        pass_accuracy = stats.get('pass_accuracy', 0)
        if pass_accuracy > 80:
            pass_bonus = self.config['pass_accuracy_bonus']
            score_breakdown['pass_accuracy_bonus'] = pass_bonus
            total_points += pass_bonus
        
        # Clean sheet bonus (if goals_conceded is 0)
        goals_conceded = stats.get('goals_conceded', 1)  # Default to 1 to avoid bonus if not provided
        if goals_conceded == 0:
            clean_sheet_points = self.config['clean_sheet']
            score_breakdown['clean_sheet'] = clean_sheet_points
            total_points += clean_sheet_points
        
        # Win bonus
        is_win = stats.get('is_win', None)
        if is_win is not None and is_win:
            win_points = self.config['win_bonus']
            score_breakdown['win_bonus'] = win_points
            total_points += win_points
        
        # Normalize to 0-100 range
        max_score = self.config['max_score']
        
        # Calculate normalized score (capped at max_score)
        normalized_score = min(total_points, max_score)
        
        return {
            'total_score': normalized_score,
            'score_breakdown': score_breakdown,
            'raw_points': total_points,
            'max_score': max_score
        }
    
    def calculate_from_ai_result(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate score directly from AI analysis result.
        
        Args:
            ai_result: Dict from AI analyzer containing match statistics
            
        Returns:
            Dict with calculated score and breakdown
        """
        # Map AI result to scoring format
        stats = {
            'goals': ai_result.get('goals', 0),
            'assists': ai_result.get('assists', 0),
            'possession': ai_result.get('possession', 50),
            'shots_on_target': ai_result.get('shots_on_target', 0),
            'pass_accuracy': ai_result.get('pass_accuracy', 0),
            'tackles': ai_result.get('tackles', 0)
        }
        
        return self.calculate_score(stats)


# Global instance with default config
default_scorer = ScoringService()


def calculate_score(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate score.
    
    Args:
        stats: Match statistics
        
    Returns:
        Dict with score calculation results
    """
    return default_scorer.calculate_score(stats)


def calculate_from_ai_result(ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate score from AI result.
    
    Args:
        ai_result: Result from AI analyzer
        
    Returns:
        Dict with score calculation results
    """
    return default_scorer.calculate_from_ai_result(ai_result)


def get_scoring_config() -> Dict[str, int]:
    """Get current scoring configuration."""
    return default_scorer.config.copy()


def update_scoring_config(config: Dict[str, int]) -> None:
    """Update scoring configuration."""
    default_scorer.config.update(config)
    logger.info(f"Scoring config updated: {default_scorer.config}")

