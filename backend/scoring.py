"""
FIFA Stats Platform - Scoring System
====================================
Calculates match scores based on extracted statistics.

Scoring Formula:
- Goals: 10 points per goal
- Shots on Target: 2 points per shot
- Tackles: 1 point per tackle
- Possession Bonus: +5 points if possession > 60%
- Pass Accuracy Bonus: +10 points if pass accuracy > 85%
"""


class ScoringSystem:
    """
    Configurable scoring system for FIFA match statistics.
    """
    
    # Default scoring weights (can be modified)
    DEFAULT_WEIGHTS = {
        'goals': 10,           # Points per goal
        'shots_on_target': 2,  # Points per shot on target
        'tackles': 1,          # Points per tackle
        'possession_bonus': 5, # Bonus if possession > threshold
        'pass_accuracy_bonus': 10  # Bonus if pass accuracy > threshold
    }
    
    # Thresholds for bonuses
    THRESHOLDS = {
        'possession': 60,      # Percentage
        'pass_accuracy': 85     # Percentage
    }
    
    def __init__(self, weights=None):
        """
        Initialize scoring system with custom weights.
        
        Args:
            weights: Dictionary of custom weights (optional)
        """
        self.weights = weights if weights else self.DEFAULT_WEIGHTS.copy()
    
    def calculate_score(self, stats):
        """
        Calculate match score based on extracted statistics.
        
        Args:
            stats: Dictionary containing:
                - goals: Number of goals
                - possession: Possession percentage
                - shots_on_target: Number of shots on target
                - pass_accuracy: Pass accuracy percentage
                - tackles: Number of tackles
        
        Returns:
            Dictionary with total_score and breakdown
        """
        score_breakdown = {
            'goals_score': 0,
            'shots_score': 0,
            'tackles_score': 0,
            'possession_bonus': 0,
            'pass_accuracy_bonus': 0,
            'total_score': 0
        }
        
        try:
            # Calculate base scores
            goals = stats.get('goals', 0)
            shots_on_target = stats.get('shots_on_target', 0)
            tackles = stats.get('tackles', 0)
            possession = stats.get('possession', 0)
            pass_accuracy = stats.get('pass_accuracy', 0)
            
            # Goals score
            score_breakdown['goals_score'] = goals * self.weights['goals']
            
            # Shots on target score
            score_breakdown['shots_score'] = shots_on_target * self.weights['shots_on_target']
            
            # Tackles score
            score_breakdown['tackles_score'] = tackles * self.weights['tackles']
            
            # Possession bonus (if > 60%)
            if possession > self.THRESHOLDS['possession']:
                score_breakdown['possession_bonus'] = self.weights['possession_bonus']
            
            # Pass accuracy bonus (if > 85%)
            if pass_accuracy > self.THRESHOLDS['pass_accuracy']:
                score_breakdown['pass_accuracy_bonus'] = self.weights['pass_accuracy_bonus']
            
            # Calculate total
            score_breakdown['total_score'] = (
                score_breakdown['goals_score'] +
                score_breakdown['shots_score'] +
                score_breakdown['tackles_score'] +
                score_breakdown['possession_bonus'] +
                score_breakdown['pass_accuracy_bonus']
            )
            
            return score_breakdown
            
        except Exception as e:
            print(f"Error calculating score: {e}")
            return score_breakdown
    
    def calculate_match_score(self, stats):
        """
        Simplified method to get just the total score.
        
        Args:
            stats: Dictionary of match statistics
            
        Returns:
            Total score as integer
        """
        result = self.calculate_score(stats)
        return result['total_score']
    
    def get_score_breakdown(self, stats):
        """
        Get detailed breakdown of score calculation.
        
        Args:
            stats: Dictionary of match statistics
            
        Returns:
            Formatted string with breakdown
        """
        breakdown = self.calculate_score(stats)
        
        lines = [
            "=== Score Breakdown ===",
            f"Goals ({stats.get('goals', 0)} × {self.weights['goals']}): {breakdown['goals_score']} pts",
            f"Shots on Target ({stats.get('shots_on_target', 0)} × {self.weights['shots_on_target']}): {breakdown['shots_score']} pts",
            f"Tackles ({stats.get('tackles', 0)} × {self.weights['tackles']}): {breakdown['tackles_score']} pts",
        ]
        
        if breakdown['possession_bonus'] > 0:
            lines.append(f"Possession Bonus (> {self.THRESHOLDS['possession']}%): +{breakdown['possession_bonus']} pts")
        
        if breakdown['pass_accuracy_bonus'] > 0:
            lines.append(f"Pass Accuracy Bonus (> {self.THRESHOLDS['pass_accuracy']}%): +{breakdown['pass_accuracy_bonus']} pts")
        
        lines.append(f"===================")
        lines.append(f"TOTAL SCORE: {breakdown['total_score']} pts")
        
        return "\n".join(lines)
    
    def update_weights(self, new_weights):
        """
        Update scoring weights.
        
        Args:
            new_weights: Dictionary of new weights
        """
        self.weights.update(new_weights)
    
    def reset_weights(self):
        """Reset weights to default values."""
        self.weights = self.DEFAULT_WEIGHTS.copy()


# Default scoring instance
default_scorer = ScoringSystem()


def calculate_match_score(stats):
    """
    Convenience function to calculate match score.
    
    Args:
        stats: Dictionary of match statistics
        
    Returns:
        Total score as integer
    """
    return default_scorer.calculate_match_score(stats)


def get_score_breakdown(stats):
    """
    Convenience function to get score breakdown.
    
    Args:
        stats: Dictionary of match statistics
        
    Returns:
        Dictionary with score breakdown
    """
    return default_scorer.calculate_score(stats)


# Example usage and testing
if __name__ == '__main__':
    # Test with sample data
    sample_stats = {
        'goals': 3,
        'possession': 65,
        'shots_on_target': 8,
        'pass_accuracy': 88,
        'tackles': 12
    }
    
    print("Sample Match Stats:")
    print(f"  Goals: {sample_stats['goals']}")
    print(f"  Possession: {sample_stats['possession']}%")
    print(f"  Shots on Target: {sample_stats['shots_on_target']}")
    print(f"  Pass Accuracy: {sample_stats['pass_accuracy']}%")
    print(f"  Tackles: {sample_stats['tackles']}")
    print()
    
    print(default_scorer.get_score_breakdown(sample_stats))
