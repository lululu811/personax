import pytest
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool

def test_signal_v2_creation():
    s = SignalV2(
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        weight=0.7,
        tags=["趋势", "技术"],
        metadata={"b1_score": 0.8}
    )
    assert s.action == SignalAction.BUY
    assert s.confidence == 0.85
    assert "趋势" in s.tags

def test_signal_action_enum():
    assert SignalAction.BUY.value == "buy"
    assert SignalAction.SELL.value == "sell"
    assert SignalAction.HOLD.value == "hold"
    assert SignalAction.NEUTRAL.value == "neutral"

def test_signal_pool_add_and_get():
    pool = SignalPool()
    s1 = SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"])
    s2 = SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["趋势"])
    pool.add(s1)
    pool.add(s2)
    assert len(pool.get_all()) == 2

def test_signal_pool_conflict_detection():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["技术"]))
    assert pool.has_conflict() == True

def test_signal_v2_confidence_validation():
    with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
        SignalV2(source="Test", action=SignalAction.BUY, confidence=1.5, weight=0.7)

def test_signal_v2_weight_validation():
    with pytest.raises(ValueError, match="weight must be 0.0-1.0"):
        SignalV2(source="Test", action=SignalAction.BUY, confidence=0.8, weight=1.5)

def test_signal_pool_no_conflict():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.BUY, confidence=0.6, weight=0.5, tags=["趋势"]))
    assert pool.has_conflict() == False

def test_signal_pool_clear():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.clear()
    assert len(pool.get_all()) == 0