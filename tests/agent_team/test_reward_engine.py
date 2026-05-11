import pytest
from unittest.mock import Mock, patch

from agent_team.core.reward import RewardEngine
from agent_team.core.models import AgentWeight


class TestRewardEngine:
    @pytest.fixture
    def engine(self):
        with patch("agent_team.core.reward.FeedbackStore") as mock_store_cls:
            mock_store = Mock()
            mock_store.get_agent_reputation.return_value = {
                "agent_name": "zettaranc",
                "tag": "技术面",
                "avg_score": 4.5,
                "sample_count": 10,
            }
            mock_store.get_weighted_scores.return_value = {
                "技术面": 4.5,
                "短线": 4.0,
            }
            mock_store_cls.return_value = mock_store
            yield RewardEngine()

    def test_get_agent_weights(self, engine):
        weights = engine.get_agent_weights(["zettaranc", "boss_mo"])
        assert "zettaranc" in weights
        assert "boss_mo" in weights
        assert weights["zettaranc"].agent_name == "zettaranc"
        assert weights["zettaranc"].reputation_score == 1.375  # _map_score_to_reputation(4.5)

    def test_get_personalized_team(self, engine):
        with patch.object(engine, "_should_explore", return_value=False):
            result = engine.get_personalized_team(
                query="帮我看看茅台的技术面",
                available_agents=["zettaranc", "boss_mo", "fupeng"],
                top_k=2,
            )
        assert len(result) == 2
        assert all(isinstance(w, AgentWeight) for w in result)

    def test_reputation_score_mapping(self):
        """Test that avg_score maps to reputation_score correctly."""
        from agent_team.core.reward import _map_score_to_reputation
        assert _map_score_to_reputation(5.0) == 1.5
        assert _map_score_to_reputation(3.0) == 1.0
        assert _map_score_to_reputation(1.0) == 0.5
