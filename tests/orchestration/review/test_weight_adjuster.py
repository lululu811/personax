# tests/orchestration/review/test_weight_adjuster.py
import pytest
from orchestration.review.weight_adjuster import WeightAdjuster
from orchestration.review.models import ReviewResult
from datetime import date


def test_compute_adjustments_increase():
    adjuster = WeightAdjuster()
    result = ReviewResult(
        period="weekly",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
        total_signals=10,
        correct=8,
        incorrect=2,
        pending=0,
        accuracy=0.8,
        by_source={"B1": {"correct": 5, "total": 6, "accuracy": 0.83}},
        weight_adjustments={},
        report=""
    )
    adjustments = adjuster.compute_adjustments(result)
    # 准确率 83% > 70%，权重应该增加
    assert adjustments.get("B1", 0) > 0


def test_compute_adjustments_decrease():
    adjuster = WeightAdjuster()
    result = ReviewResult(
        period="weekly",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
        total_signals=10,
        correct=3,
        incorrect=7,
        pending=0,
        accuracy=0.3,
        by_source={"RSI": {"correct": 2, "total": 5, "accuracy": 0.4}},
        weight_adjustments={},
        report=""
    )
    adjustments = adjuster.compute_adjustments(result)
    # 准确率 40% < 50%，权重应该减少
    assert adjustments.get("RSI", 0) < 0


def test_compute_adjustments_no_change():
    """准确率在 50-70% 之间时，权重不变"""
    adjuster = WeightAdjuster()
    result = ReviewResult(
        period="weekly",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
        total_signals=10,
        correct=5,
        incorrect=5,
        pending=0,
        accuracy=0.5,
        by_source={"MACD": {"correct": 3, "total": 5, "accuracy": 0.6}},
        weight_adjustments={},
        report=""
    )
    adjustments = adjuster.compute_adjustments(result)
    # 准确率 60% 在 50-70% 之间，权重不变
    assert adjustments.get("MACD", 0) == 0


def test_compute_adjustments_multiple_sources():
    """测试多个来源的权重调整"""
    adjuster = WeightAdjuster()
    result = ReviewResult(
        period="weekly",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
        total_signals=30,
        correct=15,
        incorrect=15,
        pending=0,
        accuracy=0.5,
        by_source={
            "B1": {"correct": 10, "total": 10, "accuracy": 1.0},    # > 70%, 增加
            "RSI": {"correct": 2, "total": 10, "accuracy": 0.2},   # < 50%, 减少
            "MACD": {"correct": 5, "total": 10, "accuracy": 0.5},   # 50-70%, 不变
        },
        weight_adjustments={},
        report=""
    )
    adjustments = adjuster.compute_adjustments(result)
    assert adjustments.get("B1", 0) > 0   # 增加
    assert adjustments.get("RSI", 0) < 0  # 减少
    assert adjustments.get("MACD", 0) == 0  # 不变