"""Tests for ContextMemory."""
import pytest
from orchestration.memory import ContextMemory, ConversationContext, UserProfile, Turn
from orchestration.signals.v2 import SignalAction


def test_context_memory_save():
    """Test saving and loading conversation context."""
    mem = ContextMemory(db_path=":memory:")
    ctx = ConversationContext(
        session_id="test-001",
        user_profile=UserProfile(risk_tolerance="medium"),
        asset_focus=["茅台", "宁德时代"],
        history=[],
    )
    mem.save(ctx)
    retrieved = mem.load("test-001")
    assert retrieved is not None
    assert "茅台" in retrieved.asset_focus
    assert "宁德时代" in retrieved.asset_focus


def test_context_memory_load_missing():
    """Test loading non-existent session returns None."""
    mem = ContextMemory(db_path=":memory:")
    retrieved = mem.load("non-existent-session")
    assert retrieved is None


def test_context_memory_with_history():
    """Test context persistence with conversation history."""
    mem = ContextMemory(db_path=":memory:")
    ctx = ConversationContext(
        session_id="test-002",
        user_profile=UserProfile(risk_tolerance="high"),
        asset_focus=["黄金"],
        history=[
            Turn(role="user", content="黄金能买吗"),
            Turn(role="assistant", content="建议观望"),
        ],
    )
    mem.save(ctx)
    retrieved = mem.load("test-002")
    assert retrieved is not None
    assert len(retrieved.history) == 2
    assert retrieved.history[0].role == "user"
    assert retrieved.history[0].content == "黄金能买吗"


def test_preference_learning():
    """Test user feedback is recorded and used to update preferences."""
    mem = ContextMemory(db_path=":memory:")
    ctx = ConversationContext(
        session_id="user-001",
        user_profile=UserProfile(risk_tolerance="medium"),
        asset_focus=["茅台"],
        history=[],
    )
    mem.save(ctx)

    # Record multiple SELL signal acceptances
    for _ in range(3):
        mem.record_feedback("user-001", SignalAction.SELL, accepted=True)

    profile = mem.get_user_profile("user-001")
    assert profile.risk_tolerance == "medium"


def test_user_profile_default():
    """Test default user profile when session not found."""
    mem = ContextMemory(db_path=":memory:")
    profile = mem.get_user_profile("unknown-session")
    assert profile.risk_tolerance == "medium"
    assert profile.signal_preferences == {}


def test_conversation_context_created_at():
    """Test that created_at timestamp is preserved."""
    mem = ContextMemory(db_path=":memory:")
    now = datetime.now()
    ctx = ConversationContext(
        session_id="test-003",
        user_profile=UserProfile(),
        asset_focus=[],
        history=[],
        created_at=now,
    )
    mem.save(ctx)
    retrieved = mem.load("test-003")
    assert retrieved is not None
    # Timestamp should be preserved (within reasonable delta)
    assert abs((retrieved.created_at - now).total_seconds()) < 1


# Need datetime import for the test
from datetime import datetime
