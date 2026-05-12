# orchestration/review/models.py
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional


class SignalAction(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    NEUTRAL = "neutral"


@dataclass
class SignalEvent:
    timestamp: datetime
    source: str
    action: SignalAction
    confidence: float
    reason: str
    price: float
    asset: str
    tags: list[str] = field(default_factory=list)


@dataclass
class SignalRecord:
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    action: SignalAction = SignalAction.HOLD
    confidence: float = 0.0
    reason: str = ""
    price: float = 0.0
    asset: str = ""
    tags: list[str] = field(default_factory=list)
    evaluated: bool = False
    outcome: Optional[str] = None
    outcome_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReviewResult:
    period: str
    start_date: date
    end_date: date
    total_signals: int = 0
    correct: int = 0
    incorrect: int = 0
    pending: int = 0
    accuracy: float = 0.0
    by_source: dict = field(default_factory=dict)
    weight_adjustments: dict = field(default_factory=dict)
    report: str = ""