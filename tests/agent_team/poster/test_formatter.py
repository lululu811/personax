from agent_team.core.models import TeamResult, Round, Thought, Synthesis
from agent_team.poster.formatter import InfographicFormatter


def test_infographic_format_basic():
    result = TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[
                    Thought(agent_name="zettaranc", content="看涨，均线多头排列", confidence=0.85),
                ],
                moderator_summary=Synthesis(
                    consensus="技术面偏多",
                    disagreements=[],
                    recommendation="关注回调机会",
                ),
            )
        ],
        final_scores={"zettaranc": 5.0},
        session_id="sess_001",
    )
    fmt = InfographicFormatter()
    md = fmt.format(result)
    assert "# PersonaX 团队分析" in md
    assert "zettaranc" in md
    assert "均线多头排列" in md
    assert "技术面偏多" in md
    assert "关注回调机会" in md
    assert "5.0" in md


def test_image_cards_format():
    from agent_team.poster.formatter import ImageCardsFormatter
    result = TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[
                    Thought(agent_name="zettaranc", content="看涨", confidence=0.9, key_points=["均线金叉", "量能放大"]),
                    Thought(agent_name="boss_mo", content="震荡", confidence=0.6, key_points=["分水未突破"]),
                ],
                moderator_summary=Synthesis(
                    consensus="谨慎看多",
                    disagreements=[],
                    recommendation="等待突破确认",
                ),
            )
        ],
        final_scores={"zettaranc": 5.0, "boss_mo": 4.0},
        session_id="sess_002",
    )
    fmt = ImageCardsFormatter()
    md = fmt.format(result)
    assert "# 封面" in md or "## 封面" in md
    assert "zettaranc" in md
    assert "boss_mo" in md
    assert "等待突破确认" in md
