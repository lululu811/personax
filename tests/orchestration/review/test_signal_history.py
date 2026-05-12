# tests/orchestration/review/test_signal_history.py
import pytest
from datetime import datetime, timedelta
from orchestration.review.signal_history import SignalHistory
from orchestration.review.models import SignalEvent, SignalRecord, SignalAction

@pytest.fixture
def fresh_history():
    """每个测试使用独立的内存数据库"""
    db_path = f":memory:{id(object())}"  # 使用对象ID确保唯一
    history = SignalHistory(db_path=db_path)
    yield history

def test_add_signal(fresh_history):
    history = fresh_history
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
    record_id = history.add(event)
    assert record_id > 0

def test_get_unevaluated(fresh_history):
    history = fresh_history
    event = SignalEvent(
        timestamp=datetime.now(),
        source="RSI",
        action=SignalAction.SELL,
        confidence=0.7,
        reason="RSI > 80",
        price=1750.0,
        asset="600519",
        tags=["动量"]
    )
    history.add(event)
    unevaluated = history.get_unevaluated()
    assert len(unevaluated) == 1
    assert unevaluated[0].source == "RSI"
    assert unevaluated[0].evaluated == False