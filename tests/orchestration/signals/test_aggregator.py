import pytest
from datetime import timedelta
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool
from orchestration.signals.aggregator import Aggregator, AggregatedResult, ConflictHandler


def test_aggregator_basic():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.BUY, confidence=0.6, weight=0.5, tags=["趋势"]))

    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())

    assert result.action == SignalAction.BUY
    assert result.confidence > 0


def test_aggregator_conflict_recent_wins():
    from datetime import datetime
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.5, weight=0.7,
                       timestamp=datetime.now() - timedelta(hours=2), tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.8, weight=0.5,
                       timestamp=datetime.now(), tags=["技术"]))

    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())
    # 近期信号应该赢
    assert result.action == SignalAction.SELL


def test_aggregator_high_confidence_wins():
    """高置信度胜出策略"""
    from datetime import datetime
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.3, weight=0.5,
                       timestamp=datetime.now() - timedelta(hours=1), tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.9, weight=0.8,
                       timestamp=datetime.now() - timedelta(hours=2), tags=["技术"]))

    agg = Aggregator(ConflictHandler.HIGH_CONFIDENCE_WINS)
    result = agg.aggregate(pool.get_all())
    assert result.action == SignalAction.SELL


def test_aggregator_weighted_voting():
    """加权投票策略"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.9, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.BUY, confidence=0.7, weight=0.8, tags=["趋势"]))
    pool.add(SignalV2(source="S1", action=SignalAction.SELL, confidence=0.6, weight=0.3, tags=["宏观"]))

    agg = Aggregator(ConflictHandler.WEIGHTED_VOTING)
    result = agg.aggregate(pool.get_all())
    assert result.action == SignalAction.BUY  # BUY 总分: 0.8*0.9 + 0.7*0.8 = 1.44 > SELL 的 0.6*0.3 = 0.18


def test_aggregator_debate_mode():
    """辩论模式返回 HOLD"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="S1", action=SignalAction.SELL, confidence=0.9, weight=0.6, tags=["技术"]))

    agg = Aggregator(ConflictHandler.DEBATE_MODE)
    result = agg.aggregate(pool.get_all())
    assert result.action == SignalAction.HOLD
    assert result.confidence == 0.5


def test_aggregator_empty_signals():
    """空信号列表"""
    agg = Aggregator()
    result = agg.aggregate([])
    assert result.action == SignalAction.NEUTRAL
    assert result.confidence == 0.0
    assert result.reasoning == "无信号"


def test_aggregator_no_conflict_hold():
    """无冲突时的 HOLD 信号"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.HOLD, confidence=0.5, weight=0.5, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.HOLD, confidence=0.6, weight=0.4, tags=["趋势"]))

    agg = Aggregator()
    result = agg.aggregate(pool.get_all())
    assert result.action == SignalAction.HOLD
    assert len(result.conflicts) == 0  # 无冲突


def test_aggregator_metadata():
    """元数据包含 handler 和 tag_groups"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术", "趋势"]))

    agg = Aggregator(ConflictHandler.WEIGHTED_VOTING)
    result = agg.aggregate(pool.get_all())
    assert result.metadata["handler"] == "weighted_voting"
    assert "技术" in result.metadata["tag_groups"]
    assert "趋势" in result.metadata["tag_groups"]