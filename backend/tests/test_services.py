"""
Tests for backend services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.services.draft_nn_service import DraftNNService, get_nn_service
from app.services.llm_prompts import LLMPromptsService, DraftContext, get_prompts_service
from app.services.champion_stats_service import ChampionStatsService


class TestDraftNNService:
    """Tests for the neural network recommendation service."""

    def test_service_initialization(self):
        """Test that NN service initializes correctly."""
        service = DraftNNService()
        assert service is not None
        assert service.model_path is not None

    def test_rule_based_scoring(self):
        """Test rule-based fallback scoring."""
        service = DraftNNService()

        champion = {
            'name': 'Aatrox',
            'win_rate': 52,
            'pick_rate': 10,
            'ban_rate': 5,
            'roles': ['TOP', 'MID'],
            'counters': {},
            'synergies': {}
        }

        draft_state = {
            'role': 'TOP',
            'phase': 'PICK',
            'current_turn': 10,
            'picks_blue': [],
            'picks_red': [],
            'side': 'BLUE'
        }

        # Test without proficiency
        score = service._rule_based_score(champion, draft_state, None)
        assert 0 <= score <= 1
        assert score > 0.3  # Should have reasonable score

        # Test with high proficiency
        score_with_prof = service._rule_based_score(champion, draft_state, 5)
        assert score_with_prof > score  # Higher proficiency should increase score

    def test_feature_extraction(self):
        """Test feature extraction for NN input."""
        service = DraftNNService()

        champion = {
            'name': 'Aatrox',
            'attack': 8,
            'defense': 5,
            'magic': 3,
            'difficulty': 4,
            'win_rate': 52,
            'pick_rate': 10,
            'ban_rate': 5,
            'roles': ['TOP'],
            'counters': {},
            'synergies': {},
            'tags': ['Fighter']
        }

        draft_state = {
            'role': 'TOP',
            'phase': 'PICK',
            'current_turn': 10,
            'picks_blue': [],
            'picks_red': [],
            'side': 'BLUE'
        }

        features = service.extract_features(champion, draft_state, 3)

        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float32
        # Should have expected number of features
        assert len(features) > 20

    def test_get_top_recommendations(self):
        """Test getting top recommendations."""
        service = DraftNNService()

        champions = [
            {'name': 'Aatrox', 'win_rate': 52, 'roles': ['TOP'], 'counters': {}, 'synergies': {}},
            {'name': 'Garen', 'win_rate': 53, 'roles': ['TOP'], 'counters': {}, 'synergies': {}},
            {'name': 'Darius', 'win_rate': 51, 'roles': ['TOP'], 'counters': {}, 'synergies': {}},
        ]

        draft_state = {
            'role': 'TOP',
            'phase': 'PICK',
            'current_turn': 10,
            'picks_blue': [],
            'picks_red': [],
            'side': 'BLUE'
        }

        recommendations = service.get_top_recommendations(
            champions, draft_state, None, top_k=3
        )

        assert len(recommendations) == 3
        assert all(isinstance(r, tuple) for r in recommendations)
        assert all(0 <= r[1] <= 1 for r in recommendations)

    def test_singleton_service(self):
        """Test that get_nn_service returns singleton."""
        service1 = get_nn_service()
        service2 = get_nn_service()
        assert service1 is service2


class TestLLMPromptsService:
    """Tests for LLM prompts generation."""

    def test_get_stage(self):
        """Test draft stage detection."""
        service = LLMPromptsService()

        assert service.get_stage(0) == 'EARLY_BAN'
        assert service.get_stage(5) == 'EARLY_BAN'
        assert service.get_stage(6) == 'FIRST_PICK'
        assert service.get_stage(10) == 'SECOND_BAN'
        assert service.get_stage(14) == 'FINAL_PICK'
        assert service.get_stage(20) == 'COMPLETE'

    def test_get_analysis_prompt(self):
        """Test analysis prompt generation."""
        service = LLMPromptsService()

        context = DraftContext(
            phase='PICK',
            turn=10,
            side='BLUE',
            role='TOP',
            elo='PLATINUM',
            bans_blue=['Yasuo', 'Yone'],
            bans_red=['Akali', 'Zed'],
            picks_blue=[{'champion': 'Jinx', 'role': 'ADC'}],
            picks_red=[{'champion': 'Kaisa', 'role': 'ADC'}]
        )

        prompt = service.get_analysis_prompt(context)

        assert 'League of Legends' in prompt
        assert 'BLUE' in prompt
        assert 'TOP' in prompt
        assert 'PLATINUM' in prompt
        assert 'Yasuo' in prompt
        assert 'Jinx' in prompt

    def test_get_recommendation_prompt(self):
        """Test recommendation prompt generation."""
        service = LLMPromptsService()

        context = DraftContext(
            phase='PICK',
            turn=10,
            side='BLUE',
            role='MID',
            elo='DIAMOND',
            bans_blue=[],
            bans_red=[],
            picks_blue=[],
            picks_red=[],
            user_champion_pool=[
                {'champion': 'Ahri', 'role': 'MID', 'proficiency': 5}
            ]
        )

        prompt = service.get_recommendation_prompt(context, 5)

        assert 'recommend' in prompt.lower()
        assert 'pick' in prompt.lower()
        assert 'MID' in prompt
        assert '5' in prompt  # num_recommendations

    def test_get_gameplan_prompt(self):
        """Test gameplan prompt generation."""
        service = LLMPromptsService()

        context = DraftContext(
            phase='COMPLETE',
            turn=20,
            side='BLUE',
            role='TOP',
            elo='PLATINUM',
            bans_blue=['Yasuo'],
            bans_red=['Akali'],
            picks_blue=[
                {'champion': 'Aatrox', 'role': 'TOP'},
                {'champion': 'Lee Sin', 'role': 'JUNGLE'},
                {'champion': 'Ahri', 'role': 'MID'},
                {'champion': 'Jinx', 'role': 'ADC'},
                {'champion': 'Thresh', 'role': 'SUPPORT'}
            ],
            picks_red=[]
        )

        prompt = service.get_gameplan_prompt(context)

        assert 'gameplan' in prompt.lower()
        assert 'BLUE' in prompt
        assert 'Aatrox' in prompt or 'Lee Sin' in prompt

    def test_singleton_prompts_service(self):
        """Test singleton pattern."""
        service1 = get_prompts_service()
        service2 = get_prompts_service()
        assert service1 is service2


class TestChampionStatsService:
    """Tests for champion stats service."""

    def test_update_champion_stats(self, test_db, test_champion):
        """Test updating champion stats."""
        service = ChampionStatsService(test_db)

        updated = service.get_champion_stats("Aatrox", "14.24")
        assert updated is not None
        assert updated.name == "Aatrox"

    def test_get_champion_stats(self, test_db, test_champion):
        """Test getting champion stats."""
        service = ChampionStatsService(test_db)

        stats = service.get_champion_stats("Aatrox")
        assert stats is not None
        assert stats.win_rate == 5100

    def test_get_nonexistent_champion(self, test_db):
        """Test getting stats for non-existent champion."""
        service = ChampionStatsService(test_db)

        stats = service.get_champion_stats("NonexistentChampion")
        assert stats is None

    def test_get_top_champions(self, test_db, multiple_champions):
        """Test getting top champions by win rate."""
        service = ChampionStatsService(test_db)

        top = service.get_top_champions_by_win_rate(limit=3)
        assert len(top) == 3
        # Should be sorted by win rate descending
        win_rates = [c.win_rate for c in top]
        assert win_rates == sorted(win_rates, reverse=True)

    def test_get_matchup_win_rate(self, test_db, test_champion):
        """Test getting matchup win rate."""
        service = ChampionStatsService(test_db)

        # Aatrox has counter data for Fiora
        wr = service.get_matchup_win_rate("Aatrox", "Fiora", "14.24")
        assert wr == 45.0  # 45 wins out of 100 games

    def test_get_synergy_win_rate(self, test_db, test_champion):
        """Test getting synergy win rate."""
        service = ChampionStatsService(test_db)

        # Aatrox has synergy data for Lee Sin
        wr = service.get_synergy_win_rate("Aatrox", "LeeSin", "14.24")
        assert wr == 54.0  # 54 wins out of 100 games
