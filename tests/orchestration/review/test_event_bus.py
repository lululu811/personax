# tests/orchestration/review/test_event_bus.py
import pytest
import time
import threading
from orchestration.review.event_bus import EventBus, emit, subscribe
from orchestration.review.models import SignalEvent, SignalAction
from datetime import datetime


def test_event_bus_emit():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("signal", handler)
    event = SignalEvent(
        timestamp=datetime.now(),
        source="test",
        action=SignalAction.BUY,
        confidence=0.8,
        reason="test",
        price=100.0,
        asset="000001",
    )
    bus.emit("signal", event)

    # Give thread time to deliver
    time.sleep(0.1)
    assert len(received) == 1
    assert received[0].source == "test"


def test_event_bus_multiple_handlers():
    bus = EventBus()
    results = []

    def handler1(event):
        results.append(("h1", event.source))

    def handler2(event):
        results.append(("h2", event.source))

    bus.subscribe("signal", handler1)
    bus.subscribe("signal", handler2)
    bus.emit("signal", SignalEvent(
        timestamp=datetime.now(),
        source="multi",
        action=SignalAction.HOLD,
        confidence=0.5,
        reason="test",
        price=50.0,
        asset="000002",
    ))

    time.sleep(0.1)
    assert len(results) == 2
    assert ("h1", "multi") in results
    assert ("h2", "multi") in results


def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("signal", handler)
    bus.unsubscribe("signal", handler)
    bus.emit("signal", SignalEvent(
        timestamp=datetime.now(),
        source="unsub",
        action=SignalAction.NEUTRAL,
        confidence=0.5,
        reason="test",
        price=10.0,
        asset="000003",
    ))

    time.sleep(0.1)
    assert len(received) == 0


def test_global_emit_subscribe():
    received = []
    handler = lambda e: received.append(e)
    subscribe("global_test", handler)
    emit("global_test", "hello")

    time.sleep(0.1)
    assert received == ["hello"]