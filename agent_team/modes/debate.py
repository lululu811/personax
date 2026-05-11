"""Debate execution mode — agents see each other's thoughts and react."""

import asyncio

from agent_team.modes.base import CollaborationMode
from agent_team.core.models import Thought, AgentContext


class DebateExecutor(CollaborationMode):
    """Executes debate mode: initial thoughts + rebuttals."""

    async def execute(self, team, query: str, context: AgentContext) -> list[Thought]:
        """Run debate: Round 1 parallel think, Round 2 parallel react."""
        # Round 1: All agents think independently
        initial_tasks = [agent.think(query, context) for agent in team.agents]
        initial_thoughts = await asyncio.gather(*initial_tasks, return_exceptions=True)

        valid_initial = []
        for agent, result in zip(team.agents, initial_thoughts):
            if isinstance(result, Exception):
                valid_initial.append(self._fallback_thought(agent.name))
            else:
                valid_initial.append(result)

        # Round 2: Each agent reacts to others' thoughts
        rebuttal_tasks = []
        for agent in team.agents:
            others = [t for t in valid_initial if t.agent_name != agent.name]
            rebuttal_tasks.append(agent.react(query, others))

        rebuttal_results = await asyncio.gather(*rebuttal_tasks, return_exceptions=True)

        valid_rebuttals = []
        for agent, result in zip(team.agents, rebuttal_results):
            if isinstance(result, Exception):
                valid_rebuttals.append(self._fallback_thought(agent.name))
            else:
                valid_rebuttals.append(result)

        return valid_initial + valid_rebuttals

    def _fallback_thought(self, agent_name: str) -> Thought:
        return Thought(
            agent_name=agent_name,
            content=f"【{agent_name} 辩论环节异常，跳过】",
            confidence=0.0,
            key_points=["辩论失败"],
            action="unknown",
            is_fallback=True,
        )
