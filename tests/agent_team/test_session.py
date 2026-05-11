import pytest
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from agent_team.core.session import TeamSession
from agent_team.core.models import SessionStatus, Thought, Round, TeamConfig


class TestTeamSession:
    @pytest.fixture
    def mock_team(self):
        agent1 = Mock()
        agent1.name = "zettaranc"
        agent2 = Mock()
        agent2.name = "boss_mo"

        moderator = Mock()
        moderator.synthesize = Mock(return_value=Mock(
            consensus="共识", disagreements=[], recommendation="建议", confidence=0.7
        ))

        team = Mock()
        team.name = "全明星"
        team.agents = [agent1, agent2]
        team.moderator = moderator
        team.mode = "parallel"
        team.get_agent = Mock(return_value=agent1)

        return team

    @pytest.mark.asyncio
    async def test_start_brainstorm(self, mock_team):
        with patch("agent_team.core.session.ParallelExecutor") as mock_executor_cls:
            mock_executor = Mock()
            mock_executor.execute = AsyncMock(return_value=[
                Thought(agent_name="zettaranc", content="看多", confidence=0.7),
                Thought(agent_name="boss_mo", content="看空", confidence=0.8),
            ])
            mock_executor_cls.return_value = mock_executor

            session = TeamSession(session_id="sess_001", team=mock_team)
            result = await session.start_brainstorm("帮我看看茅台")

            assert session.status == SessionStatus.REVIEWING
            assert result.round_num == 1
            assert len(result.thoughts) == 2
            mock_team.moderator.synthesize.assert_called_once()

    def test_start_deep_dive(self, mock_team):
        session = TeamSession(session_id="sess_001", team=mock_team)
        session.status = SessionStatus.REVIEWING

        mock_agent = mock_team.get_agent.return_value
        mock_agent.think = AsyncMock(return_value=Thought(agent_name="zettaranc", content="深入分析", confidence=0.8))

        result = session.start_deep_dive("zettaranc", "具体怎么看？")

        assert session.status == SessionStatus.DEBATING
        assert session.current_deep_dive == "zettaranc"
        assert session.current_debate_state.round_num == 0

    def test_stop_debate(self, mock_team):
        session = TeamSession(session_id="sess_001", team=mock_team)
        session.status = SessionStatus.DEBATING
        session.current_deep_dive = "zettaranc"

        session.stop_debate()

        assert session.status == SessionStatus.REVIEWING
        assert session.current_deep_dive is None

    def test_close(self, mock_team):
        with patch("agent_team.persistence.feedback_store.FeedbackStore") as mock_store_cls:
            mock_store = Mock()
            mock_store_cls.return_value = mock_store

            session = TeamSession(session_id="sess_001", team=mock_team)
            session.status = SessionStatus.REVIEWING

            result = session.close({"zettaranc": 4.5, "boss_mo": 5.0})

            assert session.status == SessionStatus.CLOSED
            assert result.final_scores == {"zettaranc": 4.5, "boss_mo": 5.0}
            mock_store.record_feedback.assert_called()

    def test_max_turns_limit(self, mock_team):
        session = TeamSession(session_id="sess_001", team=mock_team)
        session.total_turns = 10

        with pytest.raises(Exception) as exc_info:
            session.start_deep_dive("zettaranc", "问题")

        assert "最大交互次数" in str(exc_info.value)
