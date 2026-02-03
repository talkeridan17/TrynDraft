"""
Neural Network Service for Draft Recommendations
Uses champion statistics, matchups, and synergies to predict optimal picks.

Supports rank-specific models:
- Models are stored in models/{RANK}/draft_recommendation.pth
- Falls back to combined model if rank-specific model not available
- Falls back to rule-based scoring if no models available
"""
import logging
import pickle
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# Valid ranks in order of ELO
RANK_ORDER = [
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"
]

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
    """
    Service for neural network-based draft recommendations.

    Supports rank-specific models loaded dynamically based on the user's ELO.
    Falls back to combined model if rank-specific not available.
    """

    def __init__(self):
        self.models_dir = Path("models")
        self.loaded_models: Dict[str, Tuple] = {}  # rank -> (model, scaler)
        self.is_trained = False
        self._current_rank = None

        if TORCH_AVAILABLE:
            self._discover_models()
        else:
            logger.warning("PyTorch not available. Install with: pip install torch")

    def _discover_models(self):
        """Discover available trained models."""
        if not self.models_dir.exists():
            logger.info("No models directory found. Using rule-based recommendations.")
            return

        # Check for combined model
        combined_path = self.models_dir / "combined" / "draft_recommendation.pth"
        if combined_path.exists():
            self.is_trained = True
            logger.info("Found combined model")

        # Check for rank-specific models
        for rank in RANK_ORDER:
            rank_path = self.models_dir / rank / "draft_recommendation.pth"
            if rank_path.exists():
                self.is_trained = True
                logger.info(f"Found model for {rank}")

        if not self.is_trained:
            logger.info("No trained models found. Using rule-based recommendations.")

    def _get_input_size_from_metadata(self, model_dir: Path) -> int:
        """Read input size from model metadata."""
        metadata_path = model_dir / "model_metadata.json"
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get("input_size", 50)
            except Exception:
                pass
        return 50  # Default

    def _load_model_for_rank(self, rank: str) -> Tuple[Optional['DraftRecommendationNN'], Optional[object]]:
        """
        Load model for a specific rank.

        Tries rank-specific model first, falls back to combined.

        Args:
            rank: The rank to load model for (e.g., "DIAMOND")

        Returns:
            Tuple of (model, scaler) or (None, None) if not available
        """
        rank = rank.upper() if rank else "PLATINUM"

        # Check cache
        if rank in self.loaded_models:
            return self.loaded_models[rank]

        model = None
        scaler = None

        # Try rank-specific model first
        rank_model_dir = self.models_dir / rank
        rank_model_path = rank_model_dir / "draft_recommendation.pth"
        rank_scaler_path = rank_model_dir / "feature_scaler.pkl"

        if rank_model_path.exists():
            try:
                input_size = self._get_input_size_from_metadata(rank_model_dir)
                model = DraftRecommendationNN(input_size=input_size)
                model.load_state_dict(torch.load(rank_model_path, weights_only=True))
                model.eval()

                if rank_scaler_path.exists():
                    with open(rank_scaler_path, 'rb') as f:
                        scaler = pickle.load(f)

                logger.info(f"Loaded {rank} model (input_size={input_size})")
                self.loaded_models[rank] = (model, scaler)
                return model, scaler

            except Exception as e:
                logger.warning(f"Failed to load {rank} model: {e}")

        # Fall back to combined model
        combined_model_dir = self.models_dir / "combined"
        combined_model_path = combined_model_dir / "draft_recommendation.pth"
        combined_scaler_path = combined_model_dir / "feature_scaler.pkl"

        if combined_model_path.exists():
            try:
                if "combined" in self.loaded_models:
                    combined = self.loaded_models["combined"]
                    self.loaded_models[rank] = combined  # Cache for this rank too
                    return combined

                input_size = self._get_input_size_from_metadata(combined_model_dir)
                model = DraftRecommendationNN(input_size=input_size)
                model.load_state_dict(torch.load(combined_model_path, weights_only=True))
                model.eval()

                if combined_scaler_path.exists():
                    with open(combined_scaler_path, 'rb') as f:
                        scaler = pickle.load(f)

                logger.info(f"Using combined model for {rank} (input_size={input_size})")
                self.loaded_models["combined"] = (model, scaler)
                self.loaded_models[rank] = (model, scaler)
                return model, scaler

            except Exception as e:
                logger.warning(f"Failed to load combined model: {e}")

        self.loaded_models[rank] = (None, None)
        return None, None

    def get_available_models(self) -> Dict[str, bool]:
        """Get dict of which ranks have trained models."""
        available = {}
        for rank in RANK_ORDER:
            rank_path = self.models_dir / rank / "draft_recommendation.pth"
            available[rank] = rank_path.exists()

        combined_path = self.models_dir / "combined" / "draft_recommendation.pth"
        available["combined"] = combined_path.exists()

        return available

    def extract_features(
        self,
        champion: Dict,
        draft_state: Dict,
        user_proficiency: Optional[int] = None
    ) -> np.ndarray:
        """
        Extract feature vector for a champion given current draft state.

        Feature order must match nn_trainer.py exactly (48 features):
        1. attack, defense, magic, difficulty (4)
        2. win_rate, pick_rate, ban_rate (3)
        3. role_top, role_jungle, role_mid, role_adc, role_support (5 one-hot)
        4. role_flexibility (1)
        5. user_proficiency (1)
        6. is_ban_phase, turn_progress (2)
        7. matchup_1-5 (5)
        8. synergy_1-4 (4)
        9. team_has_tank/assassin/mage/marksman/support, fills_gap (6)
        10. is_tank/fighter/assassin/mage/marksman/support, early/late_game (8)
        11. tier_score, meta_relevance, skill_ceiling (3)
        12. reserved 1-6 (6)
        Total: 48

        Args:
            champion: Champion data including stats, win rates, etc.
            draft_state: Current draft state (bans, picks, phase, role)
            user_proficiency: User's proficiency with this champion (1-5)

        Returns:
            Feature vector as numpy array (48 features)
        """
        features = []
        target_role = draft_state.get('role', 'MID')
        champion_roles = champion.get('roles', [])
        champion_tags = champion.get('tags', champion_roles)  # Fallback to roles

        # 1. Champion base stats (4)
        features.extend([
            champion.get('attack', 5) / 10.0,
            champion.get('defense', 5) / 10.0,
            champion.get('magic', 5) / 10.0,
            champion.get('difficulty', 5) / 10.0,
        ])

        # 2. Meta stats (3)
        win_rate_raw = champion.get('win_rate', 50)
        win_rate = win_rate_raw / 100.0 if win_rate_raw <= 100 else win_rate_raw / 10000.0
        pick_rate_raw = champion.get('pick_rate', 5)
        pick_rate = pick_rate_raw / 100.0 if pick_rate_raw <= 100 else pick_rate_raw / 10000.0
        ban_rate_raw = champion.get('ban_rate', 5)
        ban_rate = ban_rate_raw / 100.0 if ban_rate_raw <= 100 else ban_rate_raw / 10000.0
        features.extend([win_rate, pick_rate, ban_rate])

        # 3. Role fit - one-hot encoding (5)
        # Normalize role names
        role_map = {'TOP': 'Top', 'JUNGLE': 'Jungle', 'MID': 'Mid', 'ADC': 'ADC', 'SUPPORT': 'Support'}
        normalized_roles = [r.upper() for r in champion_roles]
        features.extend([
            1.0 if 'TOP' in normalized_roles else 0.0,
            1.0 if 'JUNGLE' in normalized_roles else 0.0,
            1.0 if 'MID' in normalized_roles or 'MIDDLE' in normalized_roles else 0.0,
            1.0 if 'ADC' in normalized_roles or 'BOTTOM' in normalized_roles else 0.0,
            1.0 if 'SUPPORT' in normalized_roles or 'UTILITY' in normalized_roles else 0.0,
        ])

        # 4. Role flexibility (1)
        features.append(len(champion_roles) / 5.0)

        # 5. User proficiency (1)
        features.append((user_proficiency or 3) / 5.0)

        # 6. Draft phase context (2)
        phase = draft_state.get('phase', 'PICK')
        current_turn = draft_state.get('current_turn', 0)
        features.extend([
            1.0 if phase == 'BAN' else 0.0,
            current_turn / 20.0
        ])

        # 7. Matchup scores vs enemies (5)
        enemy_picks = draft_state.get('picks_red' if draft_state.get('side') == 'BLUE' else 'picks_blue', [])
        matchup_scores = []
        for enemy_pick in enemy_picks[:5]:
            enemy_champ = enemy_pick.get('champion', '') if isinstance(enemy_pick, dict) else enemy_pick
            matchup_wr = self._get_matchup_win_rate(champion, enemy_champ, target_role)
            matchup_scores.append(matchup_wr / 100.0 if matchup_wr else 0.5)
        while len(matchup_scores) < 5:
            matchup_scores.append(0.5)
        features.extend(matchup_scores)

        # 8. Synergy scores with allies (4)
        ally_picks = draft_state.get('picks_blue' if draft_state.get('side') == 'BLUE' else 'picks_red', [])
        synergy_scores = []
        for ally_pick in ally_picks[:4]:
            ally_champ = ally_pick.get('champion', '') if isinstance(ally_pick, dict) else ally_pick
            synergy_wr = self._get_synergy_win_rate(champion, ally_champ)
            synergy_scores.append(synergy_wr / 100.0 if synergy_wr else 0.5)
        while len(synergy_scores) < 4:
            synergy_scores.append(0.5)
        features.extend(synergy_scores)

        # 9. Team composition balance (6)
        ally_tags = []
        for ally in ally_picks:
            if isinstance(ally, dict):
                ally_tags.extend(ally.get('tags', []))
        has_tank = 1.0 if 'Tank' in ally_tags else 0.0
        has_assassin = 1.0 if 'Assassin' in ally_tags else 0.0
        has_mage = 1.0 if 'Mage' in ally_tags else 0.0
        has_marksman = 1.0 if 'Marksman' in ally_tags else 0.0
        has_support = 1.0 if 'Support' in ally_tags else 0.0
        fills_gap = 0.0
        if 'Tank' in champion_tags and not has_tank:
            fills_gap = 1.0
        elif 'Mage' in champion_tags and not has_mage:
            fills_gap = 0.8
        features.extend([has_tank, has_assassin, has_mage, has_marksman, has_support, fills_gap])

        # 10. Champion tags (8)
        features.extend([
            1.0 if 'Tank' in champion_tags else 0.0,
            1.0 if 'Fighter' in champion_tags else 0.0,
            1.0 if 'Assassin' in champion_tags else 0.0,
            1.0 if 'Mage' in champion_tags else 0.0,
            1.0 if 'Marksman' in champion_tags else 0.0,
            1.0 if 'Support' in champion_tags else 0.0,
            0.5,  # is_early_game placeholder
            0.5,  # is_late_game placeholder
        ])

        # 11. Meta position (3)
        features.extend([
            win_rate,  # tier_score
            0.5,       # meta_relevance placeholder
            0.5,       # skill_ceiling placeholder
        ])

        # 12. TARGET ROLE-SPECIFIC features (6) - CRITICAL for role-based recommendations
        # Get role-specific stats from champion data
        role_stats = champion.get('role_stats', {})
        target_role_norm = target_role.capitalize() if target_role else 'Mid'
        role_data = role_stats.get(target_role_norm, {})

        # 12a. Win rate in target role (0-1), default 0.3 if no data (penalty)
        target_role_wr_raw = role_data.get('win_rate', 30.0)
        target_role_wr = target_role_wr_raw / 100.0 if target_role_wr_raw > 1 else target_role_wr_raw
        features.append(target_role_wr)

        # 12b. Games ratio in target role vs total games (0-1)
        role_games = role_data.get('games', 0)
        total_games = champion.get('total_games', 1)
        games_ratio = role_games / max(1, total_games)
        features.append(games_ratio)

        # 12c. Log-normalized games in role
        import math
        games_log = math.log10(max(1, role_games + 1)) / 3.0
        features.append(min(1.0, games_log))

        # 12d. KDA in target role (normalized 0-1)
        kda = role_data.get('kda', 2.0)
        kda_normalized = min(1.0, kda / 5.0)
        features.append(kda_normalized)

        # 12e. Is this the champion's primary (most played) role?
        if role_stats:
            primary_role = max(role_stats.keys(), key=lambda r: role_stats.get(r, {}).get('games', 0))
            is_primary = 1.0 if target_role_norm == primary_role else 0.0
        else:
            # Fallback: check if target_role is in champion's listed roles
            is_primary = 1.0 if target_role.upper() in [r.upper() for r in champion_roles] else 0.0
        features.append(is_primary)

        # 12f. Role performance score: wr * games_ratio
        role_performance = target_role_wr * games_ratio
        features.append(role_performance)

        # Total should be 48
        assert len(features) == 48, f"Feature count mismatch: {len(features)} != 48"

        return np.array(features, dtype=np.float32)

    def _get_matchup_win_rate(self, champion: Dict, opponent: str, role: str) -> Optional[float]:
        """Get matchup win rate from champion matchups/counters data."""
        # First try scraped matchups data (role-nested structure)
        matchups = champion.get('matchups', {})
        role_matchups = matchups.get(role, matchups.get(role.capitalize(), {}))
        matchup = role_matchups.get(opponent, {})

        games = matchup.get('games', 0)
        wins = matchup.get('wins', 0)

        if games > 0:
            return (wins / games) * 100

        # Fall back to DB counters data (also role-nested)
        counters = champion.get('counters', {})
        role_counters = counters.get(role, counters.get(role.capitalize(), {}))
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
        user_proficiency: Optional[int] = None,
        rank: str = None
    ) -> float:
        """
        Predict recommendation score for a champion.

        Args:
            champion: Champion data dict
            draft_state: Current draft state
            user_proficiency: User's proficiency with champion (1-5)
            rank: User's rank for rank-specific model selection

        Returns:
            Score between 0 and 1 (higher = better recommendation)
        """
        if not TORCH_AVAILABLE or not self.is_trained:
            return self._rule_based_score(champion, draft_state, user_proficiency)

        # Get model for this rank
        model, scaler = self._load_model_for_rank(rank or "PLATINUM")

        if model is None:
            return self._rule_based_score(champion, draft_state, user_proficiency)

        # Extract features (now includes role-specific features that the NN learned from)
        features = self.extract_features(champion, draft_state, user_proficiency)

        # Normalize features if scaler is available
        if scaler:
            features = scaler.transform(features.reshape(1, -1)).flatten()

        # Convert to tensor and predict
        # The NN has learned role preferences from the training data -
        # no hardcoded boosts needed. The model knows that Zilean has
        # terrible jungle stats (low games, low WR) from the data.
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            score = model(features_tensor).item()

        # Small boost for user proficiency (they main this champ)
        if user_proficiency and user_proficiency >= 4:
            score = min(1.0, score * 1.1)  # 10% boost for high proficiency

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
        top_k: int = 5,
        rank: str = None
    ) -> List[Tuple[Dict, float]]:
        """
        Get top K champion recommendations for current draft state.

        Args:
            available_champions: List of champions not banned
            draft_state: Current draft state
            user_champion_pool: Dict of {champion_name: proficiency}
            top_k: Number of recommendations to return
            rank: User's rank for rank-specific model selection

        Returns:
            List of (champion, score) tuples, sorted by score descending
        """
        recommendations = []

        for champion in available_champions:
            champion_name = champion.get('name')
            user_prof = user_champion_pool.get(champion_name) if user_champion_pool else None

            score = self.predict_recommendation_score(champion, draft_state, user_prof, rank)
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
