from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from agent_team.cli import cli


def test_brainstorm_with_poster_generation():
    runner = CliRunner()

    with patch("agent_team.cli.Team.from_config") as mock_team_cls, \
         patch("agent_team.cli.TeamSession") as mock_session_cls, \
         patch("agent_team.cli.asyncio.run") as mock_run, \
         patch("agent_team.poster.generator.PosterGenerator") as mock_gen_cls:

        mock_team = MagicMock()
        mock_team.agents = [MagicMock(name="zettaranc")]
        mock_team.mode = "parallel"
        mock_team.get_agent.return_value = None
        mock_team_cls.return_value = mock_team

        mock_thought = MagicMock()
        mock_thought.agent_name = "zettaranc"
        mock_thought.is_fallback = False

        mock_round = MagicMock()
        mock_round.round_num = 1
        mock_round.thoughts = [mock_thought]
        mock_round.moderator_summary.consensus = "test"
        mock_round.moderator_summary.recommendation = "test"

        mock_session = MagicMock()
        mock_session.rounds = [mock_round]
        mock_session.status = "closed"
        mock_session.session_id = "sess_abc"
        mock_session.start_brainstorm = MagicMock(return_value=mock_round)
        mock_session.close.return_value.poster_paths = []
        mock_session.close.return_value.poster_text = "test poster"
        mock_session.close.return_value.session_id = "sess_abc"
        mock_session_cls.return_value = mock_session

        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value=MagicMock(files=[], errors=[]))
        mock_gen_cls.return_value = mock_gen

        # Input: skip deep-dive, score 4.5, decline poster generation
        result = runner.invoke(cli, ["brainstorm", "--query", "看看茅台"], input="skip\n4.5\nn\n")
        assert result.exit_code == 0


def test_brainstorm_accepts_poster_generation():
    runner = CliRunner()

    with patch("agent_team.cli.Team.from_config") as mock_team_cls, \
         patch("agent_team.cli.TeamSession") as mock_session_cls, \
         patch("agent_team.cli.asyncio.run") as mock_run, \
         patch("agent_team.poster.generator.PosterGenerator") as mock_gen_cls:

        mock_team = MagicMock()
        mock_team.agents = [MagicMock(name="zettaranc")]
        mock_team.mode = "parallel"
        mock_team.get_agent.return_value = None
        mock_team_cls.return_value = mock_team

        mock_thought = MagicMock()
        mock_thought.agent_name = "zettaranc"
        mock_thought.is_fallback = False

        mock_round = MagicMock()
        mock_round.round_num = 1
        mock_round.thoughts = [mock_thought]
        mock_round.moderator_summary.consensus = "test"
        mock_round.moderator_summary.recommendation = "test"

        mock_session = MagicMock()
        mock_session.rounds = [mock_round]
        mock_session.status = "closed"
        mock_session.session_id = "sess_abc"
        mock_session.start_brainstorm = MagicMock(return_value=mock_round)
        mock_session.close.return_value.poster_paths = []
        mock_session.close.return_value.poster_text = "test poster"
        mock_session.close.return_value.session_id = "sess_abc"
        mock_session_cls.return_value = mock_session

        mock_gen = MagicMock()
        mock_file = MagicMock()
        mock_file.path = "/tmp/poster.png"
        mock_file.description = "测试海报"
        mock_gen.generate = MagicMock(return_value=MagicMock(files=[mock_file], errors=[], output_dir="/tmp/posters"))
        mock_gen_cls.return_value = mock_gen

        # Input: skip deep-dive, score 4.5, accept poster generation
        result = runner.invoke(cli, ["brainstorm", "--query", "看看茅台"], input="skip\n4.5\ny\n")
        assert result.exit_code == 0
