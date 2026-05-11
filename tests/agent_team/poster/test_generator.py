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
