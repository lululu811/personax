import pytest
from unittest.mock import Mock, patch

from agent_team.core.team import Team
from agent_team.core.models import TeamConfig


class TestTeam:
    @patch("agent_team.core.team.load_persona")
    @patch("agent_team.core.team.Moderator")
    def test_team_from_config(self, mock_moderator_cls, mock_load_persona):
        mock_load_persona.return_value = Mock()
        mock_moderator_cls.return_value = Mock()

        config = TeamConfig(
            name="技术派",
            agents=["zettaranc", "boss_mo"],
            mode="parallel",
        )

        team = Team.from_config(config)

        assert team.name == "技术派"
        assert len(team.agents) == 2
        assert team.agents[0].name == "zettaranc"
        assert team.agents[1].name == "boss_mo"
        assert team.mode == "parallel"
        assert team.moderator is not None

    def test_team_get_agent(self):
        agent1 = Mock()
        agent1.name = "zettaranc"
        agent2 = Mock()
        agent2.name = "boss_mo"

        team = Team(
            name="test",
            agents=[agent1, agent2],
            mode="parallel",
            moderator=Mock(),
        )

        assert team.get_agent("zettaranc") == agent1
        assert team.get_agent("boss_mo") == agent2
        assert team.get_agent("nonexistent") is None
