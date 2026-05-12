# tests/orchestration/review/test_integration.py
import pytest
import time
from datetime import datetime, timedelta, date
from orchestration.review.event_bus import EventBus
from orchestration.review.review_service import ReviewService
from orchestration.review.models import SignalEvent, SignalAction


def test_full_pipeline():
    """完整流程: 事件 -> 存储 -> 回顾"""
    # 1. 创建独立的 EventBus 和 ReviewService
    bus = EventBus()
    service = ReviewService(db_path=":memory:")

    # 2. 订阅并处理信号事件
    def handle_signal(event):
        service.on_signal(event)

    bus.subscribe("signal", handle_signal)

    # 3. 发射事件
    event = SignalEvent(
        timestamp=datetime.now() - timedelta(days=6),
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        reason="砖块突破",
        price=1800.0,
        asset="600519",
        tags=["技术"]
    )
    bus.emit("signal", event)

    # 等待异步处理
    time.sleep(0.1)

    # 4. 验证存储
    unevaluated = service.signal_history.get_unevaluated()
    assert len(unevaluated) == 1
    assert unevaluated[0].source == "B1策略"

    # 5. 执行回顾
    result = service.review_weekly()
    assert result.total_signals == 1


def test_multiple_signals_pipeline():
    """多信号流程测试"""
    bus = EventBus()
    service = ReviewService(db_path=":memory:")

    def handle_signal(event):
        service.on_signal(event)

    bus.subscribe("signal", handle_signal)

    # 发射多个信号
    signals = [
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=i + 1),
            source="B1策略" if i % 2 == 0 else "B2策略",
            action=SignalAction.BUY if i % 3 != 0 else SignalAction.SELL,
            confidence=0.8,
            reason=f"信号{i}",
            price=1800.0,
            asset="600519",
            tags=["技术"]
        )
        for i in range(3)
    ]

    for sig in signals:
        bus.emit("signal", sig)

    time.sleep(0.1)

    unevaluated = service.signal_history.get_unevaluated()
    assert len(unevaluated) == 3

    # Mock evaluator
    service.evaluator.get_outcome_price = lambda asset, ts: 1900.0

    result = service.review_weekly()
    assert result.total_signals == 3
    assert result.pending == 0  # 所有信号都评估了


def test_period_boundary():
    """测试时间周期边界"""
    service = ReviewService(db_path=":memory:")

    # 信号在周期外（8天前）
    old_event = SignalEvent(
        timestamp=datetime.now() - timedelta(days=8),
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        reason="旧信号",
        price=1800.0,
        asset="600519",
        tags=["技术"]
    )
    service.on_signal(old_event)
    time.sleep(0.05)

    # 周回顾不应包含8天前的信号
    result = service.review_weekly()
    assert result.total_signals == 0


def test_event_bus_fire_and_forget():
    """测试 EventBus 的 Fire & Forget 特性"""
    bus = EventBus()
    service = ReviewService(db_path=":memory:")

    def handle_signal(event):
        service.on_signal(event)

    bus.subscribe("signal", handle_signal)

    # 记录处理前状态
    unevaluated_before = len(service.signal_history.get_unevaluated())

    # 发射多个快速连续的事件
    for i in range(5):
        event = SignalEvent(
            timestamp=datetime.now() - timedelta(days=3),
            source=f"策略{i}",
            action=SignalAction.BUY,
            confidence=0.85,
            reason="测试",
            price=1800.0,
            asset="600519",
            tags=[]
        )
        bus.emit("signal", event)

    # 不等待 - 验证异步处理后信号被存储
    time.sleep(0.2)

    unevaluated_after = len(service.signal_history.get_unevaluated())
    assert unevaluated_after == unevaluated_before + 5