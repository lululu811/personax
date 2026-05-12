# Signal Review System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现异步信号回顾系统，支持事件驱动接收、定期回顾、权重调整

**Architecture:** EventBus + ReviewService + SignalHistory + Evaluator + WeightAdjuster，服务分离，异步非阻塞

**Tech Stack:** Python dataclass, SQLite, Tushare (价格数据), 现有 Engine

---

## 文件结构

```
orchestration/
├── signals/
│   ├── v2.py
│   └── aggregator.py
├── memory.py
├── review/                      # 新增
│   ├── __init__.py
│   ├── models.py               # SignalEvent, SignalRecord, ReviewResult
│   ├── event_bus.py            # EventBus
│   ├── signal_history.py       # SignalHistory
│   ├── evaluator.py            # Evaluator
│   ├── weight_adjuster.py      # WeightAdjuster
│   ├── review_service.py       # ReviewService
│   └── cli.py                  # CLI 命令
├── engine.py                   # 修改：发射事件
└── legacy/
    └── signal_aggregator.py
```

---

## Task 1: Models + EventBus

### Files:
- Create: `orchestration/review/__init__.py`
- Create: `orchestration/review/models.py`
- Create: `orchestration/review/event_bus.py`
- Create: `tests/orchestration/review/test_models.py`
- Create: `tests/orchestration/review/test_event_bus.py`

### Steps:

- [ ] **Step 1: 创建目录和 `__init__.py`**

```bash
mkdir -p orchestration/review
touch orchestration/review/__init__.py
```

- [ ] **Step 2: 编写 models 测试**

```python
# tests/orchestration/review/test_models.py
import pytest
from datetime import datetime
from orchestration.review.models import SignalEvent, SignalRecord, ReviewResult, SignalAction

def test_signal_event_creation():
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
    assert event.source == "B1策略"
    assert event.action == SignalAction.BUY
    assert event.reason == "砖块突破"

def test_signal_record_creation():
    record = SignalRecord(
        id=1,
        timestamp=datetime.now(),
        source="RSI",
        action=SignalAction.SELL,
        confidence=0.7,
        reason="RSI > 80",
        price=1750.0,
        asset="600519",
        tags=["动量"]
    )
    assert record.evaluated == False
    assert record.outcome is None
```

Run: `pytest tests/orchestration/review/test_models.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 models.py**

```python
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
    outcome: Optional[str] = None  # correct/incorrect/pending
    outcome_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ReviewResult:
    period: str  # weekly/monthly
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
```

Run: `pytest tests/orchestration/review/test_models.py -v`
Expected: PASS

- [ ] **Step 4: 编写 EventBus 测试**

```python
# tests/orchestration/review/test_event_bus.py
import pytest
from orchestration.review.event_bus import EventBus
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
        asset="000001"
    )
    bus.emit("signal", event)

    assert len(received) == 1
    assert received[0].source == "test"
```

Run: `pytest tests/orchestration/review/test_event_bus.py -v`
Expected: FAIL — module not found

- [ ] **Step 5: 实现 EventBus**

```python
# orchestration/review/event_bus.py
from typing import Callable, Any
import threading

class EventBus:
    """轻量事件总线，支持 Fire & Forget"""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._queue: list[tuple[str, Any]] = []
        self._lock = threading.Lock()

    def emit(self, event_type: str, data: Any):
        """非阻塞发射事件"""
        with self._lock:
            for handler in self._handlers.get(event_type, []):
                # Fire & Forget - 在新线程中异步执行
                threading.Thread(target=handler, args=(data,), daemon=True).start()

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)


# 全局 EventBus 实例
_global_bus = EventBus()

def emit(event_type: str, data: Any):
    """全局发射事件"""
    _global_bus.emit(event_type, data)

def subscribe(event_type: str, handler: Callable):
    """全局订阅事件"""
    _global_bus.subscribe(event_type, handler)
```

Run: `pytest tests/orchestration/review/test_event_bus.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add orchestration/review/__init__.py orchestration/review/models.py orchestration/review/event_bus.py tests/orchestration/review/
git commit -m "feat(review): add EventBus and signal models"
```

---

## Task 2: SignalHistory

### Files:
- Create: `orchestration/review/signal_history.py`
- Create: `tests/orchestration/review/test_signal_history.py`

### Steps:

- [ ] **Step 1: 编写 SignalHistory 测试**

```python
# tests/orchestration/review/test_signal_history.py
import pytest
from datetime import datetime, timedelta
from orchestration.review.signal_history import SignalHistory
from orchestration.review.models import SignalEvent, SignalRecord, SignalAction

def test_add_signal():
    history = SignalHistory(db_path=":memory:")
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

def test_get_unevaluated():
    history = SignalHistory(db_path=":memory:")
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
```

Run: `pytest tests/orchestration/review/test_signal_history.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 SignalHistory**

```python
# orchestration/review/signal_history.py
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from orchestration.review.models import SignalEvent, SignalRecord, SignalAction


class SignalHistory:
    """信号历史存储"""

    def __init__(self, db_path: str = "~/.personax/review.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT NOT NULL,
                price REAL NOT NULL,
                asset TEXT NOT NULL,
                tags TEXT,
                evaluated INTEGER DEFAULT 0,
                outcome TEXT,
                outcome_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_asset ON signal_history(asset)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON signal_history(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_evaluated ON signal_history(evaluated)")
        conn.commit()
        conn.close()

    def add(self, event: SignalEvent) -> int:
        """添加信号记录"""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO signal_history (timestamp, source, action, confidence, reason, price, asset, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.timestamp.isoformat(),
            event.source,
            event.action.value,
            event.confidence,
            event.reason,
            event.price,
            event.asset,
            json.dumps(event.tags)
        ))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        return record_id

    def get_unevaluated(self) -> list[SignalRecord]:
        """获取未评估的信号"""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM signal_history WHERE evaluated = 0").fetchall()
        conn.close()
        return [self._row_to_record(row) for row in rows]

    def mark_evaluated(self, record_id: int, outcome: str, outcome_price: float):
        """标记已评估"""
        conn = self._get_conn()
        conn.execute("""
            UPDATE signal_history
            SET evaluated = 1, outcome = ?, outcome_price = ?
            WHERE id = ?
        """, (outcome, outcome_price, record_id))
        conn.commit()
        conn.close()

    def get_by_period(self, start: date, end: date) -> list[SignalRecord]:
        """按时间段获取信号"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM signal_history
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """, (start.isoformat(), end.isoformat())).fetchall()
        conn.close()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: tuple) -> SignalRecord:
        return SignalRecord(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            source=row[2],
            action=SignalAction(row[3]),
            confidence=row[4],
            reason=row[5],
            price=row[6],
            asset=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            evaluated=bool(row[9]),
            outcome=row[10],
            outcome_price=row[11],
            created_at=datetime.fromisoformat(row[12]) if row[12] else None
        )
```

Run: `pytest tests/orchestration/review/test_signal_history.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/review/signal_history.py tests/orchestration/review/
git commit -m "feat(review): add SignalHistory with SQLite persistence"
```

---

## Task 3: Evaluator

### Files:
- Create: `orchestration/review/evaluator.py`
- Create: `tests/orchestration/review/test_evaluator.py`

### Steps:

- [ ] **Step 1: 编写 Evaluator 测试**

```python
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
```

Run: `pytest tests/orchestration/review/test_evaluator.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 Evaluator**

```python
# orchestration/review/evaluator.py
from datetime import datetime, timedelta
from orchestration.review.models import SignalRecord, SignalAction


class Evaluator:
    """用技术指标验证信号对错"""

    def __init__(self, holding_days: int = 5):
        self.holding_days = holding_days

    def evaluate(self, record: SignalRecord, current_price: float) -> str:
        """评估信号对错

        逻辑：
        - BUY 信号：如果后续价格 > 信号价格，正确
        - SELL 信号：如果后续价格 < 信号价格，正确
        """
        if record.action == SignalAction.BUY:
            return "correct" if current_price > record.price else "incorrect"
        elif record.action == SignalAction.SELL:
            return "correct" if current_price < record.price else "incorrect"
        else:
            return "pending"

    def get_outcome_price(self, asset: str, signal_timestamp: datetime) -> float:
        """获取信号产生后 N 天的价格

        TODO: 接入 Tushare 获取历史价格
        目前返回模拟价格
        """
        # 占位实现，后续接入 Tushare
        return 0.0
```

Run: `pytest tests/orchestration/review/test_evaluator.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/review/evaluator.py tests/orchestration/review/
git commit -m "feat(review): add Evaluator for signal outcome verification"
```

---

## Task 4: WeightAdjuster

### Files:
- Create: `orchestration/review/weight_adjuster.py`
- Create: `tests/orchestration/review/test_weight_adjuster.py`

### Steps:

- [ ] **Step 1: 编写 WeightAdjuster 测试**

```python
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
```

Run: `pytest tests/orchestration/review/test_weight_adjuster.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 WeightAdjuster**

```python
# orchestration/review/weight_adjuster.py
from orchestration.review.models import ReviewResult


class WeightAdjuster:
    """根据历史表现调整指标权重"""

    def __init__(
        self,
        min_weight: float = 0.1,
        max_weight: float = 1.0,
        step: float = 0.1,
        high_threshold: float = 0.7,
        low_threshold: float = 0.5
    ):
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.step = step
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def compute_adjustments(self, result: ReviewResult) -> dict:
        """计算权重调整

        规则：
        - 准确率 > 70%: 权重 +0.1
        - 准确率 50-70%: 权重不变
        - 准确率 < 50%: 权重 -0.1
        """
        adjustments = {}

        for source, stats in result.by_source.items():
            accuracy = stats.get("accuracy", 0.5)
            if accuracy > self.high_threshold:
                adjustments[source] = self.step  # 增加
            elif accuracy < self.low_threshold:
                adjustments[source] = -self.step  # 减少
            else:
                adjustments[source] = 0  # 不变

        return adjustments
```

Run: `pytest tests/orchestration/review/test_weight_adjuster.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/review/weight_adjuster.py tests/orchestration/review/
git commit -m "feat(review): add WeightAdjuster for dynamic weight tuning"
```

---

## Task 5: ReviewService

### Files:
- Create: `orchestration/review/review_service.py`
- Create: `tests/orchestration/review/test_review_service.py`

### Steps:

- [ ] **Step 1: 编写 ReviewService 测试**

```python
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
```

Run: `pytest tests/orchestration/review/test_review_service.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 ReviewService**

```python
# orchestration/review/review_service.py
from datetime import datetime, date, timedelta
from orchestration.review.models import SignalEvent, ReviewResult, SignalRecord
from orchestration.review.signal_history import SignalHistory
from orchestration.review.evaluator import Evaluator
from orchestration.review.weight_adjuster import WeightAdjuster


class ReviewService:
    """信号回顾服务"""

    def __init__(
        self,
        db_path: str = "~/.personax/review.db",
        holding_days: int = 5
    ):
        self.signal_history = SignalHistory(db_path=db_path)
        self.evaluator = Evaluator(holding_days=holding_days)
        self.weight_adjuster = WeightAdjuster()

    def on_signal(self, event: SignalEvent):
        """接收信号事件，存储到数据库"""
        self.signal_history.add(event)

    def review_weekly(self) -> ReviewResult:
        """每周回顾"""
        today = date.today()
        start = today - timedelta(days=7)
        return self._review(start, today, "weekly")

    def review_monthly(self) -> ReviewResult:
        """每月回顾"""
        today = date.today()
        start = today - timedelta(days=30)
        return self._review(start, today, "monthly")

    def _review(self, start: date, end: date, period: str) -> ReviewResult:
        """执行回顾"""
        records = self.signal_history.get_by_period(start, end)

        total = len(records)
        correct = 0
        incorrect = 0
        pending = 0
        by_source = {}

        for record in records:
            # 获取事后价格并评估
            outcome_price = self.evaluator.get_outcome_price(
                record.asset, record.timestamp
            )
            if outcome_price > 0:
                outcome = self.evaluator.evaluate(record, outcome_price)
                self.signal_history.mark_evaluated(record.id, outcome, outcome_price)

                if outcome == "correct":
                    correct += 1
                elif outcome == "incorrect":
                    incorrect += 1
            else:
                pending += 1

            # 按指标统计
            if record.source not in by_source:
                by_source[record.source] = {"correct": 0, "total": 0, "accuracy": 0}
            by_source[record.source]["total"] += 1
            if outcome == "correct":
                by_source[record.source]["correct"] += 1

        # 计算准确率
        evaluated = total - pending
        accuracy = correct / evaluated if evaluated > 0 else 0.0

        # 计算各指标准确率
        for source in by_source:
            stats = by_source[source]
            stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0

        # 计算权重调整
        result = ReviewResult(
            period=period,
            start_date=start,
            end_date=end,
            total_signals=total,
            correct=correct,
            incorrect=incorrect,
            pending=pending,
            accuracy=accuracy,
            by_source=by_source,
            weight_adjustments={},
            report=self._generate_report(period, start, end, total, correct, incorrect, pending, accuracy, by_source)
        )
        result.weight_adjustments = self.weight_adjuster.compute_adjustments(result)

        return result

    def _generate_report(self, period, start, end, total, correct, incorrect, pending, accuracy, by_source) -> str:
        lines = [
            f"## {period.upper()} Review Report",
            f"Period: {start} to {end}",
            f"",
            f"Total Signals: {total}",
            f"Correct: {correct} ({accuracy*100:.1f}%)",
            f"Incorrect: {incorrect}",
            f"Pending: {pending}",
            f"",
            f"### By Source",
        ]
        for source, stats in by_source.items():
            lines.append(f"- {source}: {stats['correct']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")
        return "\n".join(lines)
```

Run: `pytest tests/orchestration/review/test_review_service.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/review/review_service.py tests/orchestration/review/
git commit -m "feat(review): add ReviewService with weekly/monthly review"
```

---

## Task 6: CLI

### Files:
- Create: `orchestration/review/cli.py`
- Create: `tests/orchestration/review/test_cli.py`

### Steps:

- [ ] **Step 1: 实现 CLI**

```python
# orchestration/review/cli.py
"""CLI for signal review system.

Usage:
    python -m orchestration.review.cli weekly
    python -m orchestration.review.cli monthly
"""
import argparse
import sys
from orchestration.review.review_service import ReviewService


def main():
    parser = argparse.ArgumentParser(description="Signal Review CLI")
    parser.add_argument(
        "period",
        choices=["weekly", "monthly"],
        help="Review period"
    )
    parser.add_argument(
        "--db-path",
        default="~/.personax/review.db",
        help="Database path"
    )
    args = parser.parse_args()

    service = ReviewService(db_path=args.db_path)

    if args.period == "weekly":
        result = service.review_weekly()
    else:
        result = service.review_monthly()

    print(result.report)
    print()
    print("Weight Adjustments:")
    for source, adjustment in result.weight_adjustments.items():
        sign = "+" if adjustment > 0 else ""
        print(f"  {source}: {sign}{adjustment}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Commit**

```bash
git add orchestration/review/cli.py
git commit -m "feat(review): add CLI for weekly/monthly review"
```

---

## Task 7: Engine 集成（发射事件）

### Files:
- Modify: `orchestration/engine.py`

### Steps:

- [ ] **Step 1: 修改 Engine 发射事件**

在 `orchestration/engine.py` 中添加：

```python
from orchestration.review.event_bus import emit as emit_signal_event
```

在 `execute()` 方法中，找到信号聚合后的位置，添加：

```python
# 发射信号事件（非阻塞）
from orchestration.review.models import SignalEvent
for signal in aggregated_signals:
    event = SignalEvent(
        timestamp=datetime.now(),
        source=signal.source,
        action=SignalAction(signal.action.value),
        confidence=signal.confidence,
        reason=signal.reason,
        price=self._get_current_price(request.stock_code),
        asset=request.stock_code,
        tags=signal.tags,
    )
    emit_signal_event("signal", event)
```

- [ ] **Step 2: Commit**

```bash
git add orchestration/engine.py
git commit -m "feat(engine): emit signal events to EventBus"
```

---

## Task 8: ReviewService 订阅事件

### Files:
- Modify: `orchestration/review/review_service.py`

### Steps:

- [ ] **Step 1: 添加订阅方法**

在 `ReviewService.__init__` 中添加：

```python
from orchestration.review.event_bus import subscribe

def start_listening(self):
    """开始监听事件"""
    subscribe("signal", self.on_signal)
```

- [ ] **Step 2: Commit**

```bash
git add orchestration/review/review_service.py
git commit -m "feat(review): subscribe to signal events"
```

---

## Task 9: 端到端集成测试

### Files:
- Create: `tests/orchestration/review/test_integration.py`

### Steps:

- [ ] **Step 1: 编写端到端测试**

```python
# tests/orchestration/review/test_integration.py
import pytest
from datetime import datetime, timedelta
from orchestration.review.event_bus import EventBus
from orchestration.review.review_service import ReviewService
from orchestration.review.models import SignalEvent, SignalAction

def test_full_pipeline():
    """完整流程: 事件 -> 存储 -> 回顾"""
    # 1. 创建 EventBus 和 ReviewService
    bus = EventBus()
    service = ReviewService(db_path=":memory:")

    # 2. 订阅
    service.start_listening()

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

    # 4. 验证存储
    unevaluated = service.signal_history.get_unevaluated()
    assert len(unevaluated) == 1

    # 5. 执行回顾
    result = service.review_weekly()
    assert result.total_signals == 1
```

Run: `pytest tests/orchestration/review/test_integration.py -v`
Expected: PASS

- [ ] **Step 2: Commit**

```bash
git add tests/orchestration/review/test_integration.py
git commit -m "test(review): add end-to-end integration tests"
```

---

## Task 10: 完整测试套件

### Steps:

- [ ] **Step 1: 运行所有测试**

```bash
pytest tests/orchestration/review/ -v
```

- [ ] **Step 2: 运行完整测试套件**

```bash
pytest tests/ -v --tb=short
```

---

## 实施检查清单

- [ ] Task 1: Models + EventBus
- [ ] Task 2: SignalHistory
- [ ] Task 3: Evaluator
- [ ] Task 4: WeightAdjuster
- [ ] Task 5: ReviewService
- [ ] Task 6: CLI
- [ ] Task 7: Engine 集成
- [ ] Task 8: EventBus 订阅
- [ ] Task 9: 端到端测试
- [ ] Task 10: 完整测试
