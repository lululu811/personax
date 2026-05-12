# tests/orchestration/review/test_models.py
import pytest
from datetime import datetime
from orchestration.review.models import SignalEvent, SignalRecord, ReviewResult, SignalAction


def test_signal_event_creation():
    event = SignalEvent(
        timestamp=datetime.now(),
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        reason="砖块突破",
        price=1800.0,
        asset="600519",
        tags=["技术"],
    )
    assert event.source == "B1策略"
    assert event.action == SignalAction.BUY
    assert event.reason == "砖块突破"


def test_signal_record_creation():
    record = SignalRecord(
        id=1,
        timestamp=datetime.now(),
        source="RSI",
        action=SignalAction.SELL,
        confidence=0.7,
        reason="RSI > 80",
        price=1750.0,
        asset="600519",
        tags=["动量"],
    )
    assert record.evaluated is False
    assert record.outcome is None


def test_signal_action_enum():
    assert SignalAction.BUY.value == "buy"
    assert SignalAction.SELL.value == "sell"
    assert SignalAction.HOLD.value == "hold"
    assert SignalAction.NEUTRAL.value == "neutral"


def test_review_result_defaults():
    from datetime import date

    result = ReviewResult(
        period="2024-Q1",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
    )
    assert result.total_signals == 0
    assert result.correct == 0
    assert result.accuracy == 0.0
    assert result.by_source == {}
    assert result.weight_adjustments == {}