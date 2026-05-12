# tests/orchestration/review/test_review_service.py
import pytest
from datetime import datetime, timedelta, date
from orchestration.review.review_service import ReviewService
from orchestration.review.models import SignalEvent, SignalAction


def test_on_signal():
    service = ReviewService(db_path=":memory:")
    event = SignalEvent(
        timestamp=datetime.now(),
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        reason="砖块突破",
        price=1800.0,
        asset="600519",
        tags=["技术"]
    )
    service.on_signal(event)
    unevaluated = service.signal_history.get_unevaluated()
    assert len(unevaluated) == 1
    assert unevaluated[0].source == "B1策略"


def test_review_weekly_empty():
    """测试空周期回顾"""
    service = ReviewService(db_path=":memory:")
    result = service.review_weekly()
    assert result.period == "weekly"
    assert result.total_signals == 0
    assert result.accuracy == 0.0


def test_review_weekly_with_records():
    """测试有记录的周期回顾"""
    service = ReviewService(db_path=":memory:")

    # 添加历史信号（使用 mock evaluator 返回固定价格）
    past = datetime.now() - timedelta(days=3)
    event = SignalEvent(
        timestamp=past,
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        reason="砖块突破",
        price=1800.0,
        asset="600519",
        tags=["技术"]
    )
    service.on_signal(event)

    # Mock evaluator 返回价格使得信号 correct
    service.evaluator.get_outcome_price = lambda asset, ts: 1900.0

    result = service.review_weekly()
    assert result.total_signals == 1
    assert result.correct == 1
    assert result.pending == 0


def test_review_monthly():
    """测试月度回顾"""
    service = ReviewService(db_path=":memory:")
    result = service.review_monthly()
    assert result.period == "monthly"
    assert result.start_date == date.today() - timedelta(days=30)
    assert result.end_date == date.today()


def test_by_source_stats():
    """测试按信号源统计"""
    service = ReviewService(db_path=":memory:")

    # 添加多个不同源信号
    for i, source in enumerate(["B1策略", "B1策略", "B2策略"]):
        past = datetime.now() - timedelta(days=i + 1)
        event = SignalEvent(
            timestamp=past,
            source=source,
            action=SignalAction.BUY,
            confidence=0.85,
            reason="测试",
            price=1800.0,
            asset="600519",
            tags=["技术"]
        )
        service.on_signal(event)

    # Mock evaluator 让 B1 全对，B2 错
    def mock_price(asset, ts):
        if ts.day % 2 == 0:
            return 1900.0
        else:
            return 1700.0

    service.evaluator.get_outcome_price = mock_price

    result = service.review_weekly()

    assert "B1策略" in result.by_source
    assert "B2策略" in result.by_source
    assert result.by_source["B1策略"]["total"] == 2
    assert result.by_source["B2策略"]["total"] == 1


def test_weight_adjustments():
    """测试权重调整"""
    service = ReviewService(db_path=":memory:")
    result = service.review_weekly()

    # 权重调整应被计算
    # 周期为空时，by_source 为空，adjustments 也应为空
    assert isinstance(result.weight_adjustments, dict)


def test_report_generation():
    """测试报告生成"""
    service = ReviewService(db_path=":memory:")
    result = service.review_weekly()

    assert "WEEKLY" in result.report or "weekly" in result.report
    assert "Period:" in result.report
    assert "Total Signals:" in result.report