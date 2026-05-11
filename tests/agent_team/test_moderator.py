import pytest
from unittest.mock import Mock, patch

from agent_team.core.moderator import Moderator
from agent_team.core.models import Thought, Synthesis


class TestModerator:
    @patch("agent_team.core.moderator.ResponseGenerator")
    def test_synthesize_parallel(self, mock_gen_cls):
        mock_gen = Mock()
        mock_gen.generate.return_value = """
共识：基本面稳健
分歧：Z哥看多 vs BOSS墨看空
建议：关注1750支撑位
"""
        mock_gen.llm_available = True
        mock_gen_cls.return_value = mock_gen

        moderator = Moderator()
        thoughts = [
            Thought(agent_name="zettaranc", content="看多，趋势转多", confidence=0.75, action="buy"),
            Thought(agent_name="boss_mo", content="看空，1800次高", confidence=0.8, action="sell"),
            Thought(agent_name="财务分析师", content="基本面稳健", confidence=0.9, action="hold"),
        ]

        result = moderator.synthesize(thoughts, "parallel")

        assert isinstance(result, Synthesis)
        assert result.consensus
        assert len(result.disagreements) >= 1
        assert result.recommendation

    def test_synthesize_template_fallback(self):
        moderator = Moderator()
        thoughts = [
            Thought(agent_name="zettaranc", content="看多", confidence=0.75, action="buy"),
            Thought(agent_name="boss_mo", content="看空", confidence=0.8, action="sell"),
        ]

        result = moderator.synthesize(thoughts, "parallel")

        assert isinstance(result, Synthesis)
        assert "分歧" in result.consensus or "分歧" in result.recommendation
