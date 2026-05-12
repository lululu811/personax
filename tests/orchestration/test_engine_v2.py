"""Tests for OrchestrationEngine with new signal and memory modules."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from orchestration.engine import (
    OrchestrationEngine,
    OrchestrationRequest,
    OrchestrationResponse,
)
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool
from orchestration.signals.aggregator import Aggregator, ConflictHandler, AggregatedResult
from orchestration.memory import ContextMemory, ConversationContext, Turn


class TestEngineIntegration:
    """Test OrchestrationEngine integration with new modules."""

    def test_engine_initialization(self):
        """Test that engine initializes with new modules."""
        with patch('shared.env_check.check_env'):
            engine = OrchestrationEngine()

            # Verify new modules are integrated
            assert hasattr(engine, 'memory')
            assert isinstance(engine.memory, ContextMemory)

            # Verify old aggregator still works
            assert hasattr(engine, 'signal_aggregator')
            # Router should exist
            assert hasattr(engine, 'router')
            # Response generator should exist
            assert hasattr(engine, 'response_generator')

    def test_engine_with_mock_data(self):
        """Test engine execute with mocked data."""
        with patch('shared.env_check.check_env'):
            engine = OrchestrationEngine()

        request = OrchestrationRequest(
            query="看看茅台",
            df=MagicMock(),
            stock_code="600519",
            persona_priority=["zettaranc"],
        )

        # Mock the internal methods to avoid actual computation
        with patch.object(engine, '_get_tools_for_query', return_value=[]):
            with patch.object(engine, '_get_strategies_for_query', return_value=[]):
                with patch.object(engine, '_compute_tools', return_value={}):
                    with patch.object(engine, '_run_strategies', return_value={}):
                        with patch.object(engine, '_build_persona_signals', return_value=[]):
                            with patch.object(engine, '_query_knowledge', return_value=[]):
                                with patch.object(engine.router, 'route') as mock_route:
                                    from orchestration.router import RouteResult
                                    mock_route.return_value = RouteResult(
                                        primary="zettaranc",
                                        secondary=[],
                                        intent="analysis",
                                        confidence=0.9,
                                        reasoning="Test routing",
                                    )

                                    from orchestration.legacy.signal_aggregator import AggregatedSignal
                                    with patch.object(engine.signal_aggregator, 'aggregate') as mock_agg:
                                        mock_agg.return_value = AggregatedSignal(
                                            action="hold",
                                            confidence=0.0,
                                            reasons=["test"],
                                            conflict_detected=False,
                                            resolution_strategy="none",
                                            persona_signals=[],
                                        )

                                        response = engine.execute(request)

                                        assert response is not None
                                        assert response.route.primary == "zettaranc"
                                        assert response.cached is False


class TestSignalPoolIntegration:
    """Test SignalPool usage in engine workflow."""

    def test_signal_pool_creation(self):
        """Test creating and using SignalPool."""
        pool = SignalPool(ttl_seconds=60)

        # Add signals
        pool.add(SignalV2(
            source="b1_strategy",
            action=SignalAction.BUY,
            confidence=0.8,
            weight=0.7,
            tags=["technical", "momentum"],
        ))
        pool.add(SignalV2(
            source="b2_strategy",
            action=SignalAction.BUY,
            confidence=0.6,
            weight=0.6,
            tags=["technical", "trend"],
        ))

        signals = pool.get_all()
        assert len(signals) == 2
        assert not pool.has_conflict()

    def test_signal_pool_conflict_detection(self):
        """Test conflict detection in SignalPool."""
        pool = SignalPool()

        pool.add(SignalV2(
            source="zettaranc",
            action=SignalAction.BUY,
            confidence=0.8,
            weight=0.7,
        ))
        pool.add(SignalV2(
            source="fupeng",
            action=SignalAction.SELL,
            confidence=0.6,
            weight=0.6,
        ))

        assert pool.has_conflict()


class TestAggregatorIntegration:
    """Test Aggregator integration."""

    def test_aggregator_basic(self):
        """Test basic signal aggregation."""
        aggregator = Aggregator()

        signals = [
            SignalV2(
                source="b1",
                action=SignalAction.BUY,
                confidence=0.8,
                weight=0.7,
            ),
            SignalV2(
                source="b2",
                action=SignalAction.BUY,
                confidence=0.6,
                weight=0.6,
            ),
        ]

        result = aggregator.aggregate(signals)

        assert result.action == SignalAction.BUY
        assert result.confidence > 0
        assert len(result.signals) == 2
        assert len(result.conflicts) == 0  # No conflict

    def test_aggregator_with_conflict(self):
        """Test aggregation with conflicting signals."""
        aggregator = Aggregator(conflict_handler=ConflictHandler.HIGH_CONFIDENCE_WINS)

        signals = [
            SignalV2(
                source="zettaranc",
                action=SignalAction.BUY,
                confidence=0.9,
                weight=0.8,
            ),
            SignalV2(
                source="fupeng",
                action=SignalAction.SELL,
                confidence=0.6,
                weight=0.6,
            ),
        ]

        result = aggregator.aggregate(signals)

        # HIGH_CONFIDENCE_WINS should pick the higher confidence signal
        assert result.action == SignalAction.BUY
        assert len(result.conflicts) > 0  # Conflict detected


class TestContextMemoryIntegration:
    """Test ContextMemory integration."""

    def test_context_memory_save_load(self, tmp_path):
        """Test saving and loading conversation context."""
        db_path = str(tmp_path / "test_memory.db")
        memory = ContextMemory(db_path=db_path)

        ctx = ConversationContext(
            session_id="test-session-123",
            history=[
                Turn(role="user", content="看看茅台"),
                Turn(role="assistant", content="茅台分析..."),
            ],
            asset_focus=["600519"],
        )

        # Save
        memory.save(ctx)

        # Load
        loaded = memory.load("test-session-123")

        assert loaded is not None
        assert loaded.session_id == "test-session-123"
        assert len(loaded.history) == 2
        assert loaded.asset_focus == ["600519"]

        memory.close()

    def test_context_memory_feedback(self, tmp_path):
        """Test recording user feedback."""
        db_path = str(tmp_path / "test_feedback.db")
        memory = ContextMemory(db_path=db_path)

        # Record feedback
        memory.record_feedback("session-1", SignalAction.BUY, accepted=True)
        memory.record_feedback("session-1", SignalAction.SELL, accepted=False)

        # Should not raise
        memory.close()

    def test_context_memory_user_profile(self, tmp_path):
        """Test getting user profile."""
        db_path = str(tmp_path / "test_profile.db")
        memory = ContextMemory(db_path=db_path)

        profile = memory.get_user_profile("non-existent-session")

        assert profile.risk_tolerance == "medium"
        assert profile.signal_preferences == {}

        memory.close()


class TestEngineMemoryPersistence:
    """Test engine's memory persistence capability."""

    def test_engine_saves_context(self, tmp_path):
        """Test that engine can save conversation context."""
        with patch('shared.env_check.check_env'):
            engine = OrchestrationEngine()

        # Use temporary memory db
        memory = ContextMemory(db_path=str(tmp_path / "engine_memory.db"))
        engine.memory = memory

        # Create a conversation context
        ctx = ConversationContext(
            session_id="engine-test-session",
            history=[
                Turn(role="user", content="帮我看看B1信号"),
            ],
        )

        # Save through engine's memory
        memory.save(ctx)

        # Load back
        loaded = memory.load("engine-test-session")
        assert loaded is not None
        assert len(loaded.history) == 1

        memory.close()


# Mark all tests that need real module imports
pytestmark = pytest.mark.integration
