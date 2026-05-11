import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from agent_team.modes.parallel import ParallelExecutor
from agent_team.core.models import Thought, AgentContext


class TestParallelExecutor:
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        agent1 = Mock()
        agent1.name = "zettaranc"
        agent1.think = AsyncMock(return_value=Thought(agent_name="zettaranc", content="看多", confidence=0.7))

        agent2 = Mock()
        agent2.name = "boss_mo"
        agent2.think = AsyncMock(return_value=Thought(agent_name="boss_mo", content="看空", confidence=0.8))

        team = Mock()
        team.agents = [agent1, agent2]

        executor = ParallelExecutor(timeout=30.0)
        results = await executor.execute(team, "帮我看看茅台", AgentContext())

        assert len(results) == 2
        assert results[0].agent_name == "zettaranc"
        assert results[1].agent_name == "boss_mo"
        agent1.think.assert_called_once()
        agent2.think.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_with_timeout(self):
        async def slow_think(*args, **kwargs):
            await asyncio.sleep(100)
            return Thought(agent_name="slow", content="slow", confidence=0.5)

        agent1 = Mock()
        agent1.name = "slow"
        agent1.think = slow_think

        team = Mock()
        team.agents = [agent1]

        executor = ParallelExecutor(timeout=0.1)
        results = await executor.execute(team, "query", AgentContext())

        assert len(results) == 1
        assert results[0].is_fallback is True
        assert "超时" in results[0].content

    @pytest.mark.asyncio
    async def test_parallel_with_exception(self):
        agent1 = Mock()
        agent1.name = "buggy"
        agent1.think = AsyncMock(side_effect=Exception("boom"))

        team = Mock()
        team.agents = [agent1]

        executor = ParallelExecutor(timeout=30.0)
        results = await executor.execute(team, "query", AgentContext())

        assert len(results) == 1
        assert results[0].is_fallback is True
