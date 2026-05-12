# tests/orchestration/review/test_evaluator.py
import pytest
from datetime import datetime, timedelta
from orchestration.review.evaluator import Evaluator
from orchestration.review.models import SignalRecord, SignalAction


def test_evaluate_buy_correct():
    eval = Evaluator()
    record = SignalRecord(
        id=1,
        timestamp=datetime.now() - timedelta(days=5),
        source="B1",
        action=SignalAction.BUY,
        confidence=0.8,
        reason="test",
        price=100.0,
        asset="000001"
    )
    # 事后价格上涨 = 正确
    outcome = eval.evaluate(record, current_price=110.0)
    assert outcome == "correct"


def test_evaluate_buy_incorrect():
    eval = Evaluator()
    record = SignalRecord(
        id=1,
        timestamp=datetime.now() - timedelta(days=5),
        source="B1",
        action=SignalAction.BUY,
        confidence=0.8,
        reason="test",
        price=100.0,
        asset="000001"
    )
    # 事后价格下跌 = 错误
    outcome = eval.evaluate(record, current_price=90.0)
    assert outcome == "incorrect"


def test_evaluate_sell_correct():
    eval = Evaluator()
    record = SignalRecord(
        id=1,
        timestamp=datetime.now() - timedelta(days=5),
        source="RSI",
        action=SignalAction.SELL,
        confidence=0.7,
        reason="test",
        price=100.0,
        asset="000001"
    )
    # 卖出后价格下跌 = 正确
    outcome = eval.evaluate(record, current_price=90.0)
    assert outcome == "correct"


def test_evaluate_hold_pending():
    eval = Evaluator()
    record = SignalRecord(
        id=1,
        timestamp=datetime.now() - timedelta(days=5),
        source="MACD",
        action=SignalAction.HOLD,
        confidence=0.5,
        reason="test",
        price=100.0,
        asset="000001"
    )
    # HOLD 信号返回 pending
    outcome = eval.evaluate(record, current_price=110.0)
    assert outcome == "pending"