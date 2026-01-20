"""
Neural Network Training Pipeline for Draft Recommendations
Trains the recommendation model using scraped champion statistics.

Supports per-rank training using data from the Riot API scraper:
- Each rank (IRON through CHALLENGER) can have its own model
- Training data is loaded from scraped_data/riot_stats/patch_X.X/{RANK}/
- Models are saved to models/{RANK}/draft_recommendation.pth
"""
import logging
import pickle
import json
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Champion
from .stats_loader import StatsLoader
from .stats_scraper import Rank, ScraperConfig
from .progress_tracker import get_progress_tracker

logger = logging.getLogger(__name__)

# PyTorch imports (optional)
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Training disabled.")

# Sklearn for preprocessing
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Some features disabled.")


class DraftDataset(Dataset):
    """PyTorch Dataset for draft training data."""

    def __init__(self, features: np.ndarray, labels: np.ndarray):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


class DraftRecommendationNN(nn.Module):
    """Neural network for draft recommendations."""

    def __init__(self, input_size: int = 50, hidden_sizes: List[int] = None):
        super().__init__()

        if hidden_sizes is None:
            hidden_sizes = [128, 64, 32]

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

        # Output layer - single score
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class NNTrainer:
    """
    Training pipeline for the draft recommendation neural network.

    Training data is generated from:
    1. Champion statistics from scraped Riot API data (per-rank)
    2. Matchup data (counter relationships)
    3. Synergy data (duo win rates)
    4. Historical draft data (if available)

    Supports per-rank models for rank-specific recommendations.
    """

    def __init__(self, rank: str = None):
        """
        Initialize the trainer.

        Args:
            rank: Specific rank to train for (e.g., "DIAMOND", "GOLD").
                  If None, trains a combined model using all available ranks.
        """
        self.rank = rank.upper() if rank else None
        self.base_model_dir = Path("models")
        self.base_model_dir.mkdir(exist_ok=True)

        # Per-rank model directories
        if self.rank:
            self.model_dir = self.base_model_dir / self.rank
        else:
            self.model_dir = self.base_model_dir / "combined"
        self.model_dir.mkdir(exist_ok=True)

        self.model_path = self.model_dir / "draft_recommendation.pth"
        self.scaler_path = self.model_dir / "feature_scaler.pkl"
        self.metadata_path = self.model_dir / "model_metadata.json"

        self.model: Optional[DraftRecommendationNN] = None
        self.scaler: Optional[StandardScaler] = None

        # Stats loader for reading scraped data
        self.stats_loader = StatsLoader()

        # Feature configuration
        self.feature_names = [
            # Champion base stats (4)
            'attack', 'defense', 'magic', 'difficulty',
            # Meta stats (3)
            'win_rate', 'pick_rate', 'ban_rate',
            # Role fit (5 - one-hot for 5 roles)
            'role_top', 'role_jungle', 'role_mid', 'role_adc', 'role_support',
            # Role flexibility (1)
            'role_flexibility',
            # User proficiency (1)
            'user_proficiency',
            # Draft phase (2)
            'is_ban_phase', 'turn_progress',
            # Matchup scores vs 5 enemies (5)
            'matchup_1', 'matchup_2', 'matchup_3', 'matchup_4', 'matchup_5',
            # Synergy scores with 4 allies (4)
            'synergy_1', 'synergy_2', 'synergy_3', 'synergy_4',
            # Team composition balance (6)
            'team_has_tank', 'team_has_assassin', 'team_has_mage',
            'team_has_marksman', 'team_has_support', 'fills_team_gap',
            # Champion tags (8)
            'is_tank', 'is_fighter', 'is_assassin', 'is_mage',
            'is_marksman', 'is_support_tag', 'is_early_game', 'is_late_game',
            # Meta position (3)
            'tier_score', 'meta_relevance', 'skill_ceiling',
            # Padding to 50 (6)
            'reserved_1', 'reserved_2', 'reserved_3', 'reserved_4', 'reserved_5', 'reserved_6'
        ]

        self.input_size = len(self.feature_names)

    def generate_training_data(self, patch: str = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate training data from scraped champion statistics.

        Loads data from scraped JSON files (not database) for accuracy.
        Supports per-rank training for rank-specific models.

        Args:
            patch: Patch version to use (latest if None)

        Returns:
            Tuple of (features, labels) as numpy arrays
        """
        # Get latest patch if not specified
        if patch is None:
            patches = self.stats_loader.get_available_patches()
            if not patches:
                logger.warning("No scraped data found. Run stats scraper first.")
                return np.array([]), np.array([])
            patch = patches[0]

        logger.info(f"Loading training data for patch {patch}")

        # Determine which ranks to use
        if self.rank:
            ranks_to_use = [self.rank]
        else:
            # Use all available ranks for combined model
            ranks_to_use = self.stats_loader.get_available_ranks(patch)

        if not ranks_to_use:
            logger.warning(f"No rank data available for patch {patch}")
            return np.array([]), np.array([])

        features = []
        labels = []
        roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
        phases = ['BAN', 'PICK']

        # Load data from each rank
        for rank in ranks_to_use:
            training_data = self.stats_loader.get_stats_for_nn_training(patch, rank)
            if not training_data:
                logger.warning(f"No training data for {rank} patch {patch}")
                continue

            champions_data = training_data.get("champions", {})
            synergy_pairs = training_data.get("synergy_pairs", [])

            logger.info(f"Processing {len(champions_data)} champions from {rank}")

            # Convert to list for easy iteration
            champ_list = list(champions_data.items())

            # Generate training examples for each champion
            for champ_name, champ_stats in champ_list:
                champ_roles = champ_stats.get("roles", {})
                matchups = champ_stats.get("matchups", {})

                for role in roles:
                    for phase in phases:
                        for turn in range(0, 20, 4):
                            feature_vec = self._extract_features_from_scraped(
                                champ_name=champ_name,
                                champ_stats=champ_stats,
                                target_role=role,
                                phase=phase,
                                turn=turn,
                                enemy_stats=[],
                                ally_stats=[],
                                user_proficiency=3
                            )

                            label = self._compute_label_from_scraped(
                                champ_stats=champ_stats,
                                target_role=role
                            )

                            features.append(feature_vec)
                            labels.append(label)

            # Generate harder examples with matchups
            for i, (champ_name, champ_stats) in enumerate(champ_list):
                other_champs = [(n, s) for j, (n, s) in enumerate(champ_list) if j != i]

                if len(other_champs) >= 9:
                    enemies = other_champs[:5]
                    allies = other_champs[5:9]

                    for role in roles:
                        feature_vec = self._extract_features_from_scraped(
                            champ_name=champ_name,
                            champ_stats=champ_stats,
                            target_role=role,
                            phase='PICK',
                            turn=12,
                            enemy_stats=enemies,
                            ally_stats=allies,
                            user_proficiency=3
                        )

                        # Compute label with matchup/synergy consideration
                        base_label = self._compute_label_from_scraped(champ_stats, role)
                        matchup_score = self._compute_matchup_score_from_scraped(
                            champ_stats, [e[0] for e in enemies]
                        )
                        synergy_score = self._compute_synergy_from_pairs(
                            champ_name, [a[0] for a in allies], synergy_pairs
                        )

                        label = 0.5 * base_label + 0.3 * matchup_score + 0.2 * synergy_score

                        features.append(feature_vec)
                        labels.append(label)

        logger.info(f"Generated {len(features)} training examples from {len(ranks_to_use)} ranks")

        return np.array(features, dtype=np.float32), np.array(labels, dtype=np.float32)

    def _extract_features_from_scraped(
        self,
        champ_name: str,
        champ_stats: Dict[str, Any],
        target_role: str,
        phase: str,
        turn: int,
        enemy_stats: List[Tuple[str, Dict]],
        ally_stats: List[Tuple[str, Dict]],
        user_proficiency: int
    ) -> np.ndarray:
        """Extract feature vector from scraped data format."""
        features = []

        # Get role-specific stats
        roles_data = champ_stats.get("roles", {})
        role_stats = roles_data.get(target_role, {})

        # Base stats (we don't have attack/defense/magic from scraping, use defaults)
        # These could be enriched from Data Dragon in the future
        features.extend([0.5, 0.5, 0.5, 0.5])  # attack, defense, magic, difficulty

        # Meta stats from scraped data
        win_rate = champ_stats.get("win_rate", 50.0) / 100.0
        total_games = champ_stats.get("total_games", 0)
        # Normalize pick rate (more games = higher pick rate relative to max)
        pick_rate = min(1.0, total_games / 1000.0) if total_games else 0.05
        ban_rate = 0.05  # Not tracked in current scraping

        features.extend([win_rate, pick_rate, ban_rate])

        # Role fit (one-hot based on which roles champion has been played in)
        features.extend([
            1.0 if 'Top' in roles_data else 0.0,
            1.0 if 'Jungle' in roles_data else 0.0,
            1.0 if 'Mid' in roles_data else 0.0,
            1.0 if 'ADC' in roles_data else 0.0,
            1.0 if 'Support' in roles_data else 0.0,
        ])

        # Role flexibility
        features.append(len(roles_data) / 5.0)

        # User proficiency
        features.append(user_proficiency / 5.0)

        # Draft phase
        features.extend([
            1.0 if phase == 'BAN' else 0.0,
            turn / 20.0
        ])

        # Matchup scores
        matchups = champ_stats.get("matchups", {})
        matchup_scores = []
        for enemy_name, _ in enemy_stats[:5]:
            score = self._get_matchup_from_scraped(matchups, target_role, enemy_name)
            matchup_scores.append(score)
        while len(matchup_scores) < 5:
            matchup_scores.append(0.5)
        features.extend(matchup_scores)

        # Synergy scores (placeholder for now)
        synergy_scores = [0.5] * 4
        features.extend(synergy_scores)

        # Team composition (placeholder)
        features.extend([0.5] * 6)

        # Champion tags (placeholder)
        features.extend([0.5] * 8)

        # Meta position
        tier_score = win_rate
        features.extend([tier_score, 0.5, 0.5])

        # Padding
        while len(features) < self.input_size:
            features.append(0.0)

        return np.array(features[:self.input_size], dtype=np.float32)

    def _get_matchup_from_scraped(
        self,
        matchups: Dict,
        role: str,
        enemy_name: str
    ) -> float:
        """Get matchup win rate from scraped matchup data."""
        if not matchups or role not in matchups:
            return 0.5

        role_matchups = matchups.get(role, {})
        if enemy_name in role_matchups:
            data = role_matchups[enemy_name]
            if data.get("games", 0) > 0:
                return data.get("win_rate", 50.0) / 100.0

        return 0.5

    def _compute_label_from_scraped(
        self,
        champ_stats: Dict[str, Any],
        target_role: str
    ) -> float:
        """Compute recommendation score label from scraped data."""
        score = 0.0

        # Win rate component (40%)
        wr = champ_stats.get("win_rate", 50.0) / 100.0
        score += wr * 0.4

        # Role fit component (30%)
        roles_data = champ_stats.get("roles", {})
        if target_role in roles_data:
            # Higher score if this is the champion's primary role
            role_games = roles_data[target_role].get("games", 0)
            total_games = champ_stats.get("total_games", 1)
            role_ratio = role_games / max(1, total_games)
            score += 0.15 + (0.15 * role_ratio)
        elif roles_data:
            score += 0.1

        # Games played as popularity indicator (20%)
        total_games = champ_stats.get("total_games", 0)
        popularity = min(1.0, total_games / 500.0)
        score += popularity * 0.2

        # Balance bonus (10%) - already high win rate is self-explanatory
        score += 0.1 * (1.0 - abs(wr - 0.5) * 2)

        return min(score, 1.0)

    def _compute_matchup_score_from_scraped(
        self,
        champ_stats: Dict[str, Any],
        enemy_names: List[str]
    ) -> float:
        """Compute average matchup score vs enemies from scraped data."""
        if not enemy_names:
            return 0.5

        matchups = champ_stats.get("matchups", {})
        scores = []

        for enemy in enemy_names:
            found = False
            for role_matchups in matchups.values():
                if enemy in role_matchups:
                    wr = role_matchups[enemy].get("win_rate", 50.0) / 100.0
                    scores.append(wr)
                    found = True
                    break
            if not found:
                scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.5

    def _compute_synergy_from_pairs(
        self,
        champ_name: str,
        ally_names: List[str],
        synergy_pairs: List[Dict]
    ) -> float:
        """Compute synergy score from synergy pair data."""
        if not ally_names or not synergy_pairs:
            return 0.5

        scores = []
        for ally in ally_names:
            found = False
            for pair in synergy_pairs:
                champs = pair.get("champions", [])
                if champ_name in champs and ally in champs:
                    wr = pair.get("win_rate", 50.0) / 100.0
                    scores.append(wr)
                    found = True
                    break
            if not found:
                scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.5

    def _extract_features(
        self,
        champion: Champion,
        target_role: str,
        phase: str,
        turn: int,
        enemy_champions: List[Champion],
        ally_champions: List[Champion],
        user_proficiency: int
    ) -> np.ndarray:
        """Extract feature vector for a champion."""
        features = []

        # Base stats (normalized 0-1)
        features.extend([
            (champion.attack or 5) / 10.0,
            (champion.defense or 5) / 10.0,
            (champion.magic or 5) / 10.0,
            (champion.difficulty or 5) / 10.0,
        ])

        # Meta stats
        features.extend([
            (champion.win_rate or 5000) / 10000.0,  # Stored as int * 100
            (champion.pick_rate or 500) / 10000.0,
            (champion.ban_rate or 500) / 10000.0,
        ])

        # Role fit (one-hot)
        champion_roles = champion.roles or []
        features.extend([
            1.0 if 'TOP' in champion_roles else 0.0,
            1.0 if 'JUNGLE' in champion_roles else 0.0,
            1.0 if 'MID' in champion_roles else 0.0,
            1.0 if 'ADC' in champion_roles else 0.0,
            1.0 if 'SUPPORT' in champion_roles else 0.0,
        ])

        # Role flexibility
        features.append(len(champion_roles) / 5.0)

        # User proficiency
        features.append(user_proficiency / 5.0)

        # Draft phase
        features.extend([
            1.0 if phase == 'BAN' else 0.0,
            turn / 20.0
        ])

        # Matchup scores (placeholder - would need actual matchup data)
        matchup_scores = []
        for enemy in enemy_champions[:5]:
            score = self._get_matchup_win_rate(champion, enemy)
            matchup_scores.append(score)
        while len(matchup_scores) < 5:
            matchup_scores.append(0.5)
        features.extend(matchup_scores)

        # Synergy scores
        synergy_scores = []
        for ally in ally_champions[:4]:
            score = self._get_synergy_win_rate(champion, ally)
            synergy_scores.append(score)
        while len(synergy_scores) < 4:
            synergy_scores.append(0.5)
        features.extend(synergy_scores)

        # Team composition (simplified)
        features.extend([0.5] * 6)  # Placeholder for team composition

        # Champion tags (simplified)
        features.extend([0.5] * 8)  # Placeholder for champion tags

        # Meta position
        tier_score = (champion.win_rate or 5000) / 10000.0
        features.extend([tier_score, 0.5, 0.5])

        # Padding
        while len(features) < self.input_size:
            features.append(0.0)

        return np.array(features[:self.input_size], dtype=np.float32)

    def _get_matchup_win_rate(self, champion: Champion, enemy: Champion) -> float:
        """Get matchup win rate from champion data."""
        if not champion.counters or not enemy.name:
            return 0.5

        for role, matchups in champion.counters.items():
            if enemy.name in matchups:
                data = matchups[enemy.name]
                games = data.get('games', 0)
                if games > 0:
                    wr = data.get('win_rate', 50)
                    return wr / 100.0

        return 0.5

    def _get_synergy_win_rate(self, champion: Champion, ally: Champion) -> float:
        """Get synergy win rate from champion data."""
        if not champion.synergies or not ally.name:
            return 0.5

        if ally.name in champion.synergies:
            data = champion.synergies[ally.name]
            games = data.get('games', 0)
            if games > 0:
                wr = data.get('win_rate', 50)
                return wr / 100.0

        return 0.5

    def _compute_label(self, champion: Champion, target_role: str) -> float:
        """Compute recommendation score label for a champion."""
        score = 0.0

        # Win rate component (40%)
        wr = (champion.win_rate or 5000) / 10000.0
        score += wr * 0.4

        # Role fit component (30%)
        champion_roles = champion.roles or []
        if target_role in champion_roles:
            score += 0.3
        elif champion_roles:
            score += 0.15

        # Pick rate as popularity indicator (20%)
        pr = (champion.pick_rate or 500) / 10000.0
        score += pr * 0.2

        # Low ban rate is good (10%)
        br = (champion.ban_rate or 500) / 10000.0
        score += (1.0 - br) * 0.1

        return min(score, 1.0)

    def _compute_matchup_score(self, champion: Champion, enemies: List[Champion]) -> float:
        """Compute average matchup score vs enemies."""
        if not enemies:
            return 0.5

        scores = [self._get_matchup_win_rate(champion, e) for e in enemies]
        return sum(scores) / len(scores)

    def _compute_synergy_score(self, champion: Champion, allies: List[Champion]) -> float:
        """Compute average synergy score with allies."""
        if not allies:
            return 0.5

        scores = [self._get_synergy_win_rate(champion, a) for a in allies]
        return sum(scores) / len(scores)

    def train(
        self,
        epochs: int = 100,
        batch_size: int = 64,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        patch: str = None
    ) -> Dict:
        """
        Train the neural network model.

        Args:
            epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate for optimizer
            validation_split: Fraction of data for validation
            patch: Patch version to train on (latest if None)

        Returns:
            Dictionary with training metrics
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available. Cannot train model.")

        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not available. Cannot preprocess data.")

        rank_info = f" for {self.rank}" if self.rank else " (combined)"
        logger.info(f"Starting neural network training{rank_info}...")

        # Initialize progress tracker
        tracker = get_progress_tracker()
        tracker.start_training(rank=self.rank, epochs=epochs)

        try:
            # Generate training data from scraped files
            features, labels = self.generate_training_data(patch=patch)

            if len(features) == 0:
                raise ValueError("No training data available. Run stats scraper first.")

            logger.info(f"Training data shape: {features.shape}")

            # Normalize features
            self.scaler = StandardScaler()
            features_scaled = self.scaler.fit_transform(features)

            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                features_scaled, labels,
                test_size=validation_split,
                random_state=42
            )

            # Create datasets
            train_dataset = DraftDataset(X_train, y_train)
            val_dataset = DraftDataset(X_val, y_val)

            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=batch_size)

            # Initialize model
            self.model = DraftRecommendationNN(input_size=self.input_size)
            criterion = nn.MSELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)

            # Training loop
            best_val_loss = float('inf')
            history = {'train_loss': [], 'val_loss': []}

            for epoch in range(epochs):
                # Training
                self.model.train()
                train_loss = 0.0

                for batch_features, batch_labels in train_loader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_features).squeeze()
                    loss = criterion(outputs, batch_labels)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

                train_loss /= len(train_loader)

                # Validation
                self.model.eval()
                val_loss = 0.0

                with torch.no_grad():
                    for batch_features, batch_labels in val_loader:
                        outputs = self.model(batch_features).squeeze()
                        loss = criterion(outputs, batch_labels)
                        val_loss += loss.item()

                val_loss /= len(val_loader)
                scheduler.step(val_loss)

                history['train_loss'].append(train_loss)
                history['val_loss'].append(val_loss)

                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self._save_model()

                # Log progress
                if (epoch + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            logger.info(f"Training complete. Best validation loss: {best_val_loss:.4f}")

            # Update progress tracker
            tracker.complete_training(
                rank=self.rank,
                val_loss=best_val_loss,
                model_path=str(self.model_path)
            )
            tracker.update_model_training(
                rank=self.rank,
                epochs=epochs,
                input_size=self.input_size,
                patch=patch
            )

            # Save metadata
            metadata = {
                'trained_at': datetime.now(timezone.utc).isoformat(),
                'rank': self.rank,
                'patch': patch or 'latest',
                'epochs': epochs,
                'batch_size': batch_size,
                'learning_rate': learning_rate,
                'input_size': self.input_size,
                'best_val_loss': best_val_loss,
                'feature_names': self.feature_names
            }
            self._save_metadata(metadata)

            return {
                'best_val_loss': best_val_loss,
                'epochs_trained': epochs,
                'history': history
            }

        except Exception as e:
            # Update tracker with error
            tracker.update_model_training(rank=self.rank, error=str(e))
            logger.error(f"Training failed: {e}")
            raise

    def _save_model(self):
        """Save model and scaler to disk."""
        if self.model is not None:
            torch.save(self.model.state_dict(), self.model_path)
            logger.info(f"Saved model to {self.model_path}")

        if self.scaler is not None:
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Saved scaler to {self.scaler_path}")

    def _save_metadata(self, metadata: Dict):
        """Save training metadata."""
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def load_model(self) -> bool:
        """Load trained model from disk."""
        if not TORCH_AVAILABLE:
            return False

        if not self.model_path.exists():
            logger.warning("No trained model found")
            return False

        try:
            self.model = DraftRecommendationNN(input_size=self.input_size)
            self.model.load_state_dict(torch.load(self.model_path))
            self.model.eval()

            if self.scaler_path.exists():
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)

            logger.info("Loaded trained model successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


# Convenience functions
def train_model(epochs: int = 100, rank: str = None) -> Dict:
    """
    Train the draft recommendation model.

    Args:
        epochs: Number of training epochs
        rank: Specific rank to train for (None for combined model)

    Returns:
        Dict with training results
    """
    trainer = NNTrainer(rank=rank)
    return trainer.train(epochs=epochs)


def train_all_ranks(epochs: int = 50) -> Dict[str, Any]:
    """
    Train separate models for each available rank.

    Returns:
        Dict with results per rank
    """
    loader = StatsLoader()
    patches = loader.get_available_patches()

    if not patches:
        return {"error": "No scraped data available"}

    patch = patches[0]
    ranks = loader.get_available_ranks(patch)

    results = {"patch": patch, "ranks": {}}

    for rank in ranks:
        logger.info(f"Training model for {rank}...")
        try:
            trainer = NNTrainer(rank=rank)
            result = trainer.train(epochs=epochs, patch=patch)
            results["ranks"][rank] = {
                "status": "success",
                "best_val_loss": result.get("best_val_loss"),
                "model_path": str(trainer.model_path)
            }
        except Exception as e:
            results["ranks"][rank] = {
                "status": "error",
                "error": str(e)
            }
            logger.error(f"Failed to train {rank}: {e}")

    # Also train combined model
    logger.info("Training combined model...")
    try:
        trainer = NNTrainer(rank=None)
        result = trainer.train(epochs=epochs, patch=patch)
        results["combined"] = {
            "status": "success",
            "best_val_loss": result.get("best_val_loss"),
            "model_path": str(trainer.model_path)
        }
    except Exception as e:
        results["combined"] = {
            "status": "error",
            "error": str(e)
        }

    return results


def get_available_models() -> Dict[str, Any]:
    """Get list of available trained models."""
    base_dir = Path("models")
    if not base_dir.exists():
        return {"models": []}

    models = []
    for model_dir in base_dir.iterdir():
        if model_dir.is_dir():
            model_path = model_dir / "draft_recommendation.pth"
            metadata_path = model_dir / "model_metadata.json"

            if model_path.exists():
                model_info = {"rank": model_dir.name, "path": str(model_path)}

                if metadata_path.exists():
                    try:
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                            model_info["trained_at"] = metadata.get("trained_at")
                            model_info["patch"] = metadata.get("patch")
                            model_info["best_val_loss"] = metadata.get("best_val_loss")
                    except Exception:
                        pass

                models.append(model_info)

    return {"models": models}


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    if len(sys.argv) > 1:
        rank = sys.argv[1].upper()
        if rank == "ALL":
            result = train_all_ranks(epochs=50)
        else:
            result = train_model(epochs=50, rank=rank)
    else:
        # Default: train combined model
        result = train_model(epochs=50)

    print(f"\nTraining complete: {json.dumps(result, indent=2, default=str)}")
