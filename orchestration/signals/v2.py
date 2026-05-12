from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalAction(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    NEUTRAL = "neutral"


@dataclass
class SignalV2:
    source: str
    action: SignalAction
    confidence: float  # 0.0-1.0
    weight: float     # 0.0-1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0.0-1.0")
        if not 0 <= self.weight <= 1:
            raise ValueError("weight must be 0.0-1.0")


class SignalPool:
    def __init__(self, ttl_seconds: Optional[int] = None):
        self._signals: list[SignalV2] = []
        self.ttl_seconds = ttl_seconds

    def add(self, signal: SignalV2):
        self._signals.append(signal)

    def get_all(self) -> list[SignalV2]:
        if self.ttl_seconds is None:
            return list(self._signals)
        now = datetime.now()
        return [s for s in self._signals
                if (now - s.timestamp).total_seconds() < self.ttl_seconds]

    def has_conflict(self) -> bool:
        actions = set(s.action for s in self.get_all())
        return len(actions) > 1 and SignalAction.BUY in actions and SignalAction.SELL in actions

    def clear(self):
        self._signals.clear()