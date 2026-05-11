"""Base class for collaboration modes."""

from abc import ABC, abstractmethod

from agent_team.core.models import Thought, AgentContext


class CollaborationMode(ABC):
    """Abstract base for team collaboration modes."""

    @abstractmethod
    async def execute(self, team, query: str, context: AgentContext) -> list[Thought]:
        """Execute the collaboration mode.

        Args:
            team: Team instance with agents
            query: User's query
            context: Shared context for all agents

        Returns:
            List of thoughts from all agents
        """
        pass
