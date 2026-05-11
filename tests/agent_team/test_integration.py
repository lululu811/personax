# tests/agent_team/test_integration.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from agent_team.core.models import TeamConfig, SessionStatus
from agent_team.core.team import Team
from agent_team.core.session import TeamSession


class TestIntegration:
    """End-to-end integration test with mocked LLM."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock ResponseGenerator to avoid real LLM calls."""
        with patch("agent_team.core.agent.ResponseGenerator") as mock_gen_cls, \
             patch("agent_team.core.moderator.ResponseGenerator") as mock_mod_gen_cls:

            mock_gen = Mock()
            mock_gen.llm_available = True
            mock_gen.generate.return_value = "这是一个模拟的分析回答。看多，建议关注量能。"
            mock_gen_cls.return_value = mock_gen
            mock_mod_gen_cls.return_value = mock_gen

            yield mock_gen

    @pytest.mark.asyncio
    async def test_full_parallel_session(self, mock_llm_response):
        config = TeamConfig(
            name="测试团队",
            agents=["zettaranc"],  # Single agent for simplicity
            mode="parallel",
        )

        with patch("agent_team.core.team.load_persona") as mock_load:
            mock_persona = Mock()
            mock_persona.to_system_prompt.return_value = "你是Z哥"
            mock_load.return_value = mock_persona

            team = Team.from_config(config)
            session = TeamSession(session_id="test_001", team=team)

            # Start brainstorm
            round_result = await session.start_brainstorm("帮我看看茅台")

            assert session.status == SessionStatus.REVIEWING
            assert len(round_result.thoughts) == 1
            assert round_result.thoughts[0].agent_name == "zettaranc"

            # Close with scores
            result = session.close({"zettaranc": 4.5})

            assert session.status == SessionStatus.CLOSED
            assert result.final_scores == {"zettaranc": 4.5}
            assert result.poster_text is not None
