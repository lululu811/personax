"""CLI entry point for team brainstorming."""

import asyncio
import uuid

import click

from agent_team.core.models import TeamConfig, SessionStatus
from agent_team.core.team import Team
from agent_team.core.session import TeamSession


TEAM_TEMPLATES = {
    "全明星": ["zettaranc", "fupeng", "boss_mo", "financial_analyst"],
    "技术派": ["zettaranc", "boss_mo"],
    "基本面派": ["financial_analyst", "fupeng"],
    "快问快答": "auto",
}


@click.group()
def cli():
    """PersonaX Agent Team — Multi-persona brainstorming CLI."""
    pass


@cli.command()
@click.option("--query", "-q", required=True, help="Your analysis query")
@click.option("--template", "-t", default="全明星", help="Team template name")
@click.option("--agents", "-a", help="Comma-separated agent names (overrides template)")
@click.option("--mode", "-m", default="parallel", type=click.Choice(["parallel", "debate"]))
@click.option("--stock-code", "-s", help="Stock code for data analysis")
def brainstorm(query, template, agents, mode, stock_code):
    """Start a team brainstorming session."""
    asyncio.run(_brainstorm(query, template, agents, mode, stock_code))


async def _brainstorm(query, template, agents, mode, stock_code):
    # Determine agent list
    if agents:
        agent_list = [a.strip() for a in agents.split(",")]
    elif template in TEAM_TEMPLATES:
        agent_list = TEAM_TEMPLATES[template]
        if agent_list == "auto":
            # TODO: Use RewardEngine to auto-select
            agent_list = ["zettaranc", "financial_analyst"]
    else:
        agent_list = ["zettaranc"]

    config = TeamConfig(
        name=template or "custom",
        agents=agent_list,
        mode=mode,
    )

    click.echo(f"组建团队: {', '.join(agent_list)} (模式: {mode})")
    click.echo("-" * 50)

    team = Team.from_config(config)
    session = TeamSession(session_id=f"sess_{uuid.uuid4().hex[:8]}", team=team)

    # Start brainstorming
    round_result = await session.start_brainstorm(query)

    # Display results
    click.echo(f"\n第 {round_result.round_num} 轮分析结果:\n")
    for thought in round_result.thoughts:
        icon = " " if not thought.is_fallback else "!"
        click.echo(f"{icon} 【{thought.agent_name}】")
        click.echo(f"   {thought.content[:200]}...")
        click.echo(f"   置信度: {thought.confidence:.0%}")
        click.echo()

    # Moderator summary
    summary = round_result.moderator_summary
    click.echo("主持人汇总:")
    click.echo(f"   共识: {summary.consensus}")
    click.echo(f"   建议: {summary.recommendation}")
    click.echo()

    # Interactive deep-dive loop
    while session.status != SessionStatus.CLOSED:
        click.echo("选项: [Agent名称] 深入讨论 | [skip] 跳过 | [close] 结束评分")
        choice = click.prompt("你的选择", default="skip")

        if choice.lower() == "skip":
            break
        elif choice.lower() == "close":
            _do_scoring(session)
            break
        elif choice in [a.name for a in team.agents]:
            await _deep_dive(session, choice)
        else:
            click.echo("无效的选项")

    if session.status != SessionStatus.CLOSED:
        _do_scoring(session)

    click.echo("\n会话结束")


async def _deep_dive(session: TeamSession, agent_name: str):
    """Interactive deep-dive with a specific agent."""
    click.echo(f"\n进入与 {agent_name} 的深入讨论 (最多3轮)")

    while True:
        user_input = click.prompt("你的问题 (或 '结束')")
        if user_input.lower() in ["结束", "end", "stop"]:
            session.stop_debate()
            break

        try:
            session.start_deep_dive(agent_name, user_input)
        except Exception as e:
            click.echo(f"! {e}")
            break

        debate_round = await session.debate_turn(user_input)
        response = debate_round.agent_response

        click.echo(f"\n【{agent_name}】")
        click.echo(f"   {response.content}")

        if debate_round.max_rounds_reached:
            click.echo("\n已达到最大辩论轮次")
            session.stop_debate()
            break

    click.echo()


def _do_scoring(session: TeamSession):
    """Collect user scores for each agent."""
    click.echo("\n请为参与的 Agent 打分 (1-5星，回车跳过):\n")

    scores = {}
    for thought in session.rounds[-1].thoughts if session.rounds else []:
        if thought.is_fallback:
            continue
        score_str = click.prompt(f"  {thought.agent_name}", default="", show_default=False)
        if score_str.strip():
            try:
                score = float(score_str)
                if 1.0 <= score <= 5.0:
                    scores[thought.agent_name] = score
            except ValueError:
                pass

    if scores:
        result = session.close(scores)
        click.echo("\n最终报告:")
        click.echo(result.poster_text)

        if click.confirm("\n是否生成海报？", default=False):
            asyncio.run(_generate_posters(result))
    else:
        session.status = SessionStatus.CLOSED


async def _generate_posters(result):
    from agent_team.poster.generator import PosterGenerator, DEFAULT_STYLES

    generator = PosterGenerator()
    missing = generator._check_prerequisites()
    if missing:
        click.echo(f"! 缺少技能: {', '.join(missing)}")
        click.echo("  安装: claude skill install baoyu-infographic baoyu-image-cards")
        return

    click.echo("生成海报中...（3种风格并行）\n")
    output = await generator.generate(result, styles=DEFAULT_STYLES)

    for f in output.files:
        click.echo(f"  ✓ {f.description}: {f.path}")
    for e in output.errors:
        click.echo(f"  ✗ {e.style_id}: {e.error}")

    if output.files:
        result.poster_paths = [str(f.path) for f in output.files]
        click.echo(f"\n海报保存在: {output.output_dir}")


if __name__ == "__main__":
    cli()
