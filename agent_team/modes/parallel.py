"""Parallel execution mode — all agents think simultaneously."""

import asyncio

from agent_team.modes.base import CollaborationMode
from agent_team.core.models import Thought, AgentContext


class ParallelExecutor(CollaborationMode):
    """Executes all agents in parallel with individual timeouts."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def execute(self, team, query: str, context: AgentContext) -> list[Thought]:
        """Run all agents' think() in parallel."""
        tasks = [
            self._run_agent(agent, query, context)
            for agent in team.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        thoughts = []
        for agent, result in zip(team.agents, results):
            if isinstance(result, Exception):
                thoughts.append(self._fallback_thought(agent.name, f"分析异常: {result}"))
            else:
                thoughts.append(result)

        return thoughts

    async def _run_agent(self, agent, query: str, context: AgentContext) -> Thought:
        """Run a single agent with timeout."""
        try:
            return await asyncio.wait_for(
                agent.think(query, context),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return self._fallback_thought(agent.name, "分析超时")

    def _fallback_thought(self, agent_name: str, reason: str) -> Thought:
        return Thought(
            agent_name=agent_name,
            content=f"【{agent_name} {reason}，暂时无法参与分析】",
            confidence=0.0,
            key_points=["分析失败"],
            action="unknown",
            is_fallback=True,
        )
