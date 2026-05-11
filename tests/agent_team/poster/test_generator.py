import pytest
from unittest.mock import patch, AsyncMock

from agent_team.core.models import TeamResult, Round, Thought, Synthesis
from agent_team.poster.generator import PosterGenerator
from agent_team.poster.styles import PosterStyle


@pytest.fixture
def sample_result():
    return TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[Thought(agent_name="z", content="看涨", confidence=0.8)],
                moderator_summary=Synthesis(consensus="多", disagreements=[], recommendation="买"),
            )
        ],
        final_scores={"z": 5.0},
        session_id="sess_test",
    )


@pytest.fixture
def sample_style():
    return PosterStyle(
        style_id="test-style",
        skill_name="baoyu-test",
        args=["--no-confirm"],
        output_subdir="test",
        description="测试",
    )


@pytest.mark.asyncio
async def test_generate_single_success(sample_result, sample_style, tmp_path):
    gen = PosterGenerator(output_dir=str(tmp_path))

    with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_exec.return_value = mock_proc

        result = await gen._generate_single(sample_result, sample_style, tmp_path / "sess_test")
        assert result.style_id == "test-style"


@pytest.mark.asyncio
async def test_generate_parallel_mixed_results(sample_result, tmp_path):
    gen = PosterGenerator(output_dir=str(tmp_path))

    with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = AsyncMock()
            if call_count == 1:
                proc.wait = AsyncMock(return_value=0)
                # Create a fake png
                (tmp_path / "sess_test" / "infographic-tech").mkdir(parents=True, exist_ok=True)
                (tmp_path / "sess_test" / "infographic-tech" / "infographic.png").write_text("")
            else:
                proc.wait = AsyncMock(return_value=1)
            return proc

        mock_exec.side_effect = side_effect

        output = await gen.generate(sample_result)
        assert len(output.files) + len(output.errors) == 3


def test_prerequisites_detects_missing_skills():
    gen = PosterGenerator()
    with patch("pathlib.Path.exists", return_value=False):
        missing = gen._check_prerequisites()
        assert len(missing) == 2  # 2 unique skill names across 3 default styles (baoyu-infographic appears twice)
