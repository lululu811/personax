# tests/agent_team/test_models.py
import pytest
from dataclasses import asdict
from agent_team.core.models import (
    Thought, AgentContext, Synthesis, TeamResult,
    Round, DebateRound, SessionStatus, HealthResult,
    TeamConfig, ConflictStrategy
)


def test_thought_creation():
    t = Thought(
        agent_name="zettaranc",
        content="月线四块砖翻红",
        confidence=0.75,
        key_points=["趋势转多"],
        action="buy",
    )
    assert t.agent_name == "zettaranc"
    assert t.confidence == 0.75
    assert t.is_rebuttal is False


def test_agent_context_defaults():
    ctx = AgentContext()
    assert ctx.tool_results is None
    assert ctx.strategy_results is None
    assert ctx.knowledge_snippets is None


def test_session_status_enum():
    assert SessionStatus.IDLE.value == "idle"
    assert SessionStatus.REVIEWING.value == "reviewing"


def test_team_config_creation():
    cfg = TeamConfig(
        name="全明星",
        agents=["zettaranc", "boss_mo"],
        mode="parallel",
    )
    assert cfg.name == "全明星"
    assert cfg.moderator_persona == "moderator"
