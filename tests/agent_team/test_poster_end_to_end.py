"""End-to-end test for poster generation flow."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from agent_team.core.models import TeamConfig, SessionStatus, TeamResult
from agent_team.core.team import Team
from agent_team.core.session import TeamSession
from agent_team.poster.generator import PosterGenerator


class TestPosterEndToEnd:
    """Test full session → poster flow with mocked dependencies."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock ResponseGenerator to avoid real LLM calls."""
        with patch("agent_team.core.agent.ResponseGenerator") as mock_gen_cls, \
             patch("agent_team.core.moderator.ResponseGenerator") as mock_mod_gen_cls:

            mock_gen = Mock()
            mock_gen.llm_available = True
            mock_gen.generate.return_value = "技术面偏多，均线多头排列，建议关注量能变化。"
            mock_gen_cls.return_value = mock_gen
            mock_mod_gen_cls.return_value = mock_gen

            yield mock_gen

    @pytest.mark.asyncio
    async def test_full_session_with_poster_generation(self, mock_llm_response, tmp_path):
        """Full flow: brainstorm → close → generate posters → verify paths."""
        config = TeamConfig(
            name="测试团队",
            agents=["zettaranc", "boss_mo"],
            mode="parallel",
        )

        with patch("agent_team.core.team.load_persona") as mock_load:
            mock_persona = Mock()
            mock_persona.to_system_prompt.return_value = "你是分析师"
            mock_load.return_value = mock_persona

            team = Team.from_config(config)
            session = TeamSession(session_id="e2e_test_001", team=team)

            # Step 1: Brainstorm
            round_result = await session.start_brainstorm("帮我看看茅台")
            assert session.status == SessionStatus.REVIEWING
            assert len(round_result.thoughts) == 2

            # Step 2: Close with scores
            result = session.close({"zettaranc": 5.0, "boss_mo": 4.0})
            assert session.status == SessionStatus.CLOSED
            assert result.final_scores == {"zettaranc": 5.0, "boss_mo": 4.0}
            assert result.poster_text is not None
            assert result.poster_paths == []  # Not populated yet

            # Step 3: Generate posters (mocked subprocess)
            generator = PosterGenerator(output_dir=str(tmp_path))

            with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
                call_count = 0

                async def side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    proc = AsyncMock()
                    proc.returncode = 0
                    proc.communicate = AsyncMock(return_value=(b"", b""))
                    # Create fake PNGs for each style - must match generator's expected filename: report.png
                    style_dir = tmp_path / "e2e_test_001"
                    if call_count == 1:
                        (style_dir / "infographic-tech").mkdir(parents=True, exist_ok=True)
                        (style_dir / "infographic-tech" / "report.png").write_text("")
                    elif call_count == 2:
                        (style_dir / "infographic-pro").mkdir(parents=True, exist_ok=True)
                        (style_dir / "infographic-pro" / "report.png").write_text("")
                    else:
                        (style_dir / "image-cards").mkdir(parents=True, exist_ok=True)
                        (style_dir / "image-cards" / "report.png").write_text("")
                    return proc

                mock_exec.side_effect = side_effect

                output = await generator.generate(result)

                # Verify all 3 styles were attempted
                assert call_count == 3

                # Verify successful generations (4 styles: 3 baoyu + 1 html which always succeeds)
                assert len(output.files) == 4
                assert len(output.errors) == 0

                # Verify file paths exist
                for f in output.files:
                    assert f.path.exists(), f"File not found: {f.path}"

                # Step 4: Populate poster_paths (as CLI does)
                result.poster_paths = [str(f.path) for f in output.files]
                assert len(result.poster_paths) == 4  # 3 baoyu styles + 1 html
                assert all(".png" in p or ".html" in p for p in result.poster_paths)

    @pytest.mark.asyncio
    async def test_poster_generation_with_missing_skills(self, tmp_path):
        """Test that prerequisites check detects missing skills."""
        generator = PosterGenerator(output_dir=str(tmp_path))

        with patch("pathlib.Path.exists", return_value=False):
            missing = generator._check_prerequisites()
            assert len(missing) == 2  # 2 unique skill names
            assert "baoyu-infographic" in missing
            assert "baoyu-image-cards" in missing

    @pytest.mark.asyncio
    async def test_poster_generation_partial_failure(self, tmp_path):
        """Test that one style failure doesn't block others."""
        result = TeamResult(
            rounds=[],
            final_scores={},
            session_id="partial_test",
        )

        generator = PosterGenerator(output_dir=str(tmp_path))

        with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            call_count = 0

            async def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                proc = AsyncMock()
                if call_count == 1:
                    # First style succeeds - must use report.png to match generator expectation
                    proc.returncode = 0
                    proc.communicate = AsyncMock(return_value=(b"", b""))
                    (tmp_path / "partial_test" / "infographic-tech").mkdir(parents=True, exist_ok=True)
                    (tmp_path / "partial_test" / "infographic-tech" / "report.png").write_text("")
                else:
                    # Others fail
                    proc.returncode = 1
                    proc.communicate = AsyncMock(return_value=(b"", b"error msg"))
                return proc

            mock_exec.side_effect = side_effect

            output = await generator.generate(result)

            # infographic-tech succeeds, html-modern always succeeds, others fail
            assert len(output.files) == 2
            assert len(output.errors) == 2
            assert output.files[0].style_id == "infographic-tech"
            assert output.files[1].style_id == "html-modern"

    def test_formatter_output_structure(self):
        """Verify formatter produces valid markdown structure."""
        from agent_team.poster.formatter import InfographicFormatter, ImageCardsFormatter
        from agent_team.core.models import TeamResult, Round, Thought, Synthesis

        result = TeamResult(
            rounds=[
                Round(
                    round_num=1,
                    thoughts=[
                        Thought(agent_name="zettaranc", content="看涨，突破前高", confidence=0.9),
                        Thought(agent_name="boss_mo", content="观望，分水未突破", confidence=0.5),
                    ],
                    moderator_summary=Synthesis(
                        consensus="谨慎看多",
                        disagreements=[],
                        recommendation="等待放量确认",
                    ),
                )
            ],
            final_scores={"zettaranc": 5.0, "boss_mo": 3.0},
            session_id="fmt_test",
        )

        # Infographic formatter
        inf_fmt = InfographicFormatter()
        inf_md = inf_fmt.format(result)
        assert "# PersonaX" in inf_md
        assert "zettaranc" in inf_md
        assert "boss_mo" in inf_md
        assert "谨慎看多" in inf_md
        assert "等待放量确认" in inf_md

        # Image cards formatter
        card_fmt = ImageCardsFormatter()
        card_md = card_fmt.format(result)
        assert "封面" in card_md
        assert "zettaranc" in card_md
        assert "boss_mo" in card_md
        assert "总结" in card_md
