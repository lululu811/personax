"""Team composition and factory."""

from agent_team.core.models import TeamConfig
from agent_team.core.agent import Agent
from agent_team.core.moderator import Moderator
from personas.persona_loader import load_persona


class Team:
    """A team of Agents with a moderator."""

    def __init__(self, name: str, agents: list[Agent], mode: str, moderator: Moderator):
        self.name = name
        self.agents = agents
        self.mode = mode
        self.moderator = moderator

    def get_agent(self, name: str) -> Agent | None:
        """Get an agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    @classmethod
    def from_config(cls, config: TeamConfig) -> "Team":
        """Create a Team from a TeamConfig."""
        agents = []
        for agent_name in config.agents:
            try:
                persona_config = load_persona(agent_name)
                agents.append(Agent(name=agent_name, persona_config=persona_config))
            except Exception as e:
                # Log warning but don't fail — team can work with partial agents
                import logging
                logging.warning(f"Failed to load persona {agent_name}: {e}")

        # Load moderator persona if specified
        moderator_config = None
        if config.moderator_persona != "moderator":
            try:
                moderator_config = load_persona(config.moderator_persona)
            except Exception:
                pass

        moderator = Moderator(persona_config=moderator_config)

        return cls(
            name=config.name,
            agents=agents,
            mode=config.mode,
            moderator=moderator,
        )
