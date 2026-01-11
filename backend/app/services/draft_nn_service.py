"""
Neural Network Service for Draft Recommendations
Uses champion statistics, matchups, and synergies to predict optimal picks
"""
import logging
import pickle
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# Try to import ML libraries (optional dependencies)
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Neural network recommendations disabled.")


class DraftRecommendationNN(nn.Module):
    """
    Neural network for draft recommendations.

    Input features:
    - Champion base stats (attack, defense, magic, difficulty)
    - Current draft state (bans, picks by role)
    - Matchup win rates vs enemy picks
    - Synergy win rates with ally picks
    - User proficiency with champion
    - Champion win rate, pick rate, ban rate

    Output:
    - Recommendation score (0-1) for each available champion
    """

    def __init__(self, input_size: int = 50, hidden_sizes: List[int] = [128, 64, 32]):
        super(DraftRecommendationNN, self).__init__()

        # Build network layers
        layers = []
        prev_size = input_size

        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(0.3)
            ])
            prev_size = hidden_size

        # Output layer
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class DraftNNService:
    """Service for neural network-based draft recommendations."""

    def __init__(self):
        self.model = None
        self.model_path = Path("models/draft_recommendation.pth")
        self.scaler_path = Path("models/feature_scaler.pkl")
        self.feature_scaler = None
        self.is_trained = False

        if TORCH_AVAILABLE:
            self._load_model()
        else:
            logger.warning("PyTorch not available. Install with: pip install torch")

    def _load_model(self):
        """Load trained model from disk if available."""
        if self.model_path.exists():
            try:
                self.model = DraftRecommendationNN()
                self.model.load_state_dict(torch.load(self.model_path))
                self.model.eval()

                # Load feature scaler
                if self.scaler_path.exists():
                    with open(self.scaler_path, 'rb') as f:
                        self.feature_scaler = pickle.load(f)

                self.is_trained = True
                logger.info("Loaded trained draft recommendation model")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.model = None
        else:
            logger.info("No trained model found. Using rule-based recommendations.")

    def extract_features(
        self,
        champion: Dict,
        draft_state: Dict,
        user_proficiency: Optional[int] = None
    ) -> np.ndarray:
        """
        Extract feature vector for a champion given current draft state.

        Args:
            champion: Champion data including stats, win rates, etc.
            draft_state: Current draft state (bans, picks, phase, role)
            user_proficiency: User's proficiency with this champion (1-5)

        Returns:
            Feature vector as numpy array
        """
        features = []

        # 1. Champion base stats (normalized 0-1)
        features.extend([
            champion.get('attack', 5) / 10.0,
            champion.get('defense', 5) / 10.0,
            champion.get('magic', 5) / 10.0,
            champion.get('difficulty', 5) / 10.0,
        ])

        # 2. Champion meta statistics
        features.extend([
            champion.get('win_rate', 50) / 100.0,
            champion.get('pick_rate', 10) / 100.0,
            champion.get('ban_rate', 5) / 100.0,
        ])

        # 3. User proficiency (0 if not logged in)
        features.append((user_proficiency or 0) / 5.0)

        # 4. Role fit (one-hot encoding for 5 roles)
        target_role = draft_state.get('role', 'MID')
        champion_roles = champion.get('roles', [])
        role_fit = [
            1.0 if target_role in champion_roles else 0.5,
            len(champion_roles) / 5.0  # Role flexibility
        ]
        features.extend(role_fit)

        # 5. Draft phase context
        phase = draft_state.get('phase', 'PICK')
        current_turn = draft_state.get('current_turn', 0)
        features.extend([
            1.0 if phase == 'BAN' else 0.0,
            current_turn / 20.0  # Normalized turn number
        ])

        # 6. Matchup considerations (vs enemy picks)
        enemy_picks = draft_state.get('picks_red' if draft_state.get('side') == 'BLUE' else 'picks_blue', [])
        matchup_scores = []
        for enemy_pick in enemy_picks[:5]:  # Max 5 enemies
            enemy_champ = enemy_pick.get('champion', '')
            # Look up matchup win rate from champion.counters
            matchup_wr = self._get_matchup_win_rate(champion, enemy_champ, target_role)
            matchup_scores.append(matchup_wr / 100.0 if matchup_wr else 0.5)

        # Pad to 5 enemies
        while len(matchup_scores) < 5:
            matchup_scores.append(0.5)
        features.extend(matchup_scores)

        # 7. Synergy considerations (with ally picks)
        ally_picks = draft_state.get('picks_blue' if draft_state.get('side') == 'BLUE' else 'picks_red', [])
        synergy_scores = []
        for ally_pick in ally_picks[:4]:  # Max 4 allies (excluding current pick)
            ally_champ = ally_pick.get('champion', '')
            synergy_wr = self._get_synergy_win_rate(champion, ally_champ)
            synergy_scores.append(synergy_wr / 100.0 if synergy_wr else 0.5)

        # Pad to 4 allies
        while len(synergy_scores) < 4:
            synergy_scores.append(0.5)
        features.extend(synergy_scores)

        # 8. Team composition balance (damage types, tankiness)
        ally_tags = []
        for ally in ally_picks:
            ally_tags.extend(ally.get('tags', []))

        has_tank = 1.0 if 'Tank' in ally_tags else 0.0
        has_assassin = 1.0 if 'Assassin' in ally_tags else 0.0
        has_mage = 1.0 if 'Mage' in ally_tags else 0.0
        has_marksman = 1.0 if 'Marksman' in ally_tags else 0.0
        has_support = 1.0 if 'Support' in ally_tags else 0.0

        champion_tags = champion.get('tags', [])
        fills_gap = 0.0
        if 'Tank' in champion_tags and not has_tank:
            fills_gap = 1.0
        elif 'Mage' in champion_tags and not has_mage:
            fills_gap = 0.8
        elif 'Marksman' in champion_tags and not has_marksman:
            fills_gap = 0.8

        features.extend([has_tank, has_assassin, has_mage, has_marksman, has_support, fills_gap])

        return np.array(features, dtype=np.float32)

    def _get_matchup_win_rate(self, champion: Dict, opponent: str, role: str) -> Optional[float]:
        """Get matchup win rate from champion counters data."""
        counters = champion.get('counters', {})
        role_counters = counters.get(role, {})
        matchup = role_counters.get(opponent, {})

        games = matchup.get('games', 0)
        wins = matchup.get('wins', 0)

        if games > 0:
            return (wins / games) * 100
        return None

    def _get_synergy_win_rate(self, champion: Dict, ally: str) -> Optional[float]:
        """Get synergy win rate from champion synergies data."""
        synergies = champion.get('synergies', {})
        synergy = synergies.get(ally, {})

        games = synergy.get('games', 0)
        wins = synergy.get('wins', 0)

        if games > 0:
            return (wins / games) * 100
        return None

    def predict_recommendation_score(
        self,
        champion: Dict,
        draft_state: Dict,
        user_proficiency: Optional[int] = None
    ) -> float:
        """
        Predict recommendation score for a champion.

        Returns:
            Score between 0 and 1 (higher = better recommendation)
        """
        if not TORCH_AVAILABLE or not self.is_trained:
            # Fallback to rule-based scoring
            return self._rule_based_score(champion, draft_state, user_proficiency)

        # Extract features
        features = self.extract_features(champion, draft_state, user_proficiency)

        # Normalize features if scaler is available
        if self.feature_scaler:
            features = self.feature_scaler.transform(features.reshape(1, -1)).flatten()

        # Convert to tensor
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            score = self.model(features_tensor).item()

        return score

    def _rule_based_score(
        self,
        champion: Dict,
        draft_state: Dict,
        user_proficiency: Optional[int] = None
    ) -> float:
        """
        Fallback rule-based scoring when neural network is not available.

        Scoring factors:
        - Win rate: 30%
        - User proficiency: 25%
        - Role fit: 20%
        - Matchups: 15%
        - Synergies: 10%
        """
        score = 0.0

        # Win rate component (30%)
        win_rate = champion.get('win_rate', 50)
        score += (win_rate / 100.0) * 0.3

        # User proficiency component (25%)
        if user_proficiency:
            score += (user_proficiency / 5.0) * 0.25
        else:
            score += 0.125  # Neutral if no user data

        # Role fit component (20%)
        target_role = draft_state.get('role', 'MID')
        champion_roles = champion.get('roles', [])
        if target_role in champion_roles:
            score += 0.2
        elif champion_roles:
            score += 0.1  # Partial credit for off-role

        # Matchups component (15%)
        # TODO: Calculate average matchup win rate vs enemy picks
        score += 0.075  # Neutral for now

        # Synergies component (10%)
        # TODO: Calculate average synergy win rate with ally picks
        score += 0.05  # Neutral for now

        return min(score, 1.0)

    def get_top_recommendations(
        self,
        available_champions: List[Dict],
        draft_state: Dict,
        user_champion_pool: Optional[Dict[str, int]] = None,
        top_k: int = 5
    ) -> List[Tuple[Dict, float]]:
        """
        Get top K champion recommendations for current draft state.

        Args:
            available_champions: List of champions not banned
            draft_state: Current draft state
            user_champion_pool: Dict of {champion_name: proficiency}
            top_k: Number of recommendations to return

        Returns:
            List of (champion, score) tuples, sorted by score descending
        """
        recommendations = []

        for champion in available_champions:
            champion_name = champion.get('name')
            user_prof = user_champion_pool.get(champion_name) if user_champion_pool else None

            score = self.predict_recommendation_score(champion, draft_state, user_prof)
            recommendations.append((champion, score))

        # Sort by score descending
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:top_k]


# Global service instance
_nn_service = None


def get_nn_service() -> DraftNNService:
    """Get singleton instance of DraftNNService."""
    global _nn_service
    if _nn_service is None:
        _nn_service = DraftNNService()
    return _nn_service
