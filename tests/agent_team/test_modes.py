import pytest
from unittest.mock import Mock, AsyncMock

from agent_team.modes.base import CollaborationMode
from agent_team.core.models import Thought, AgentContext


class MockMode(CollaborationMode):
    async def execute(self, team, query, context):
        return [
            Thought(agent_name="a1", content="test", confidence=0.5),
        ]


class TestCollaborationMode:
    @pytest.mark.asyncio
    async def test_mock_mode_execution(self):
        mode = MockMode()
        team = Mock()
        team.agents = []
        result = await mode.execute(team, "query", AgentContext())
        assert len(result) == 1
        assert result[0].agent_name == "a1"
