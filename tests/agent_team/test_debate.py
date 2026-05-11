import pytest
from unittest.mock import Mock, AsyncMock

from agent_team.modes.debate import DebateExecutor
from agent_team.core.models import Thought, AgentContext


class TestDebateExecutor:
    @pytest.mark.asyncio
    async def test_debate_execution(self):
        agent1 = Mock()
        agent1.name = "zettaranc"
        agent1.think = AsyncMock(return_value=Thought(agent_name="zettaranc", content="看多", confidence=0.7))
        agent1.react = AsyncMock(return_value=Thought(agent_name="zettaranc", content="反驳", confidence=0.7, is_rebuttal=True))

        agent2 = Mock()
        agent2.name = "boss_mo"
        agent2.think = AsyncMock(return_value=Thought(agent_name="boss_mo", content="看空", confidence=0.8))
        agent2.react = AsyncMock(return_value=Thought(agent_name="boss_mo", content="反驳", confidence=0.8, is_rebuttal=True))

        team = Mock()
        team.agents = [agent1, agent2]

        executor = DebateExecutor()
        results = await executor.execute(team, "帮我看看茅台", AgentContext())

        # Should have 4 thoughts: 2 initial + 2 rebuttals
        assert len(results) == 4
        initial = [t for t in results if not t.is_rebuttal]
        rebuttals = [t for t in results if t.is_rebuttal]
        assert len(initial) == 2
        assert len(rebuttals) == 2
