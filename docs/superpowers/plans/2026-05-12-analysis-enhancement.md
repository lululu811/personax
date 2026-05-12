# Analysis Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构信号聚合引擎，支持置信度评分、上下文记忆、多源实时数据接入

**Architecture:** 新建 `orchestration/signals/` 包，包含 SignalV2 + SignalPool + Aggregator；新建 `orchestration/memory.py` 实现上下文记忆；重构 `orchestration/engine.py` 使用新模块

**Tech Stack:** Python dataclass, SQLite (persist), Tushare (行情), 新闻 API (舆情)

---

## 文件结构

```
orchestration/
├── signals/
│   ├── __init__.py          # 导出
│   ├── v2.py                 # SignalV2, SignalAction, SignalPool
│   └── aggregator.py         # Aggregator, AggregatedResult, ConflictStrategy
├── memory.py                 # ContextMemory, ConversationContext
├── engine.py                 # 重构使用新信号模块
├── signal_aggregator.py     # 旧代码 → legacy/ (确认后删除)
├── conversation.py           # 保持不变
├── router.py                # 保持不变
└── response_generator.py    # 支持新格式
```

---

## Task 1: SignalV2 数据结构

**Files:**
- Create: `orchestration/signals/v2.py`
- Create: `tests/orchestration/signals/test_v2.py`

- [ ] **Step 1: 创建目录和空 `__init__.py`**

```bash
mkdir -p orchestration/signals
touch orchestration/signals/__init__.py
```

- [ ] **Step 2: 编写 SignalV2 单元测试**

```python
# tests/orchestration/signals/test_v2.py
import pytest
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool

def test_signal_v2_creation():
    s = SignalV2(
        source="B1策略",
        action=SignalAction.BUY,
        confidence=0.85,
        weight=0.7,
        tags=["趋势", "技术"],
        metadata={"b1_score": 0.8}
    )
    assert s.action == SignalAction.BUY
    assert s.confidence == 0.85
    assert "趋势" in s.tags

def test_signal_action_enum():
    assert SignalAction.BUY.value == "buy"
    assert SignalAction.SELL.value == "sell"
    assert SignalAction.HOLD.value == "hold"
    assert SignalAction.NEUTRAL.value == "neutral"
```

Run: `pytest tests/orchestration/signals/test_v2.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 SignalV2 和 SignalAction**

```python
# orchestration/signals/v2.py
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
```

Run: `pytest tests/orchestration/signals/test_v2.py -v`
Expected: PASS

- [ ] **Step 4: 编写 SignalPool 测试**

```python
# tests/orchestration/signals/test_v2.py (追加)
def test_signal_pool_add_and_get():
    pool = SignalPool()
    s1 = SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"])
    s2 = SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["趋势"])
    pool.add(s1)
    pool.add(s2)
    assert len(pool.get_all()) == 2

def test_signal_pool_conflict_detection():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["技术"]))
    assert pool.has_conflict() == True
```

- [ ] **Step 5: 实现 SignalPool**

```python
# orchestration/signals/v2.py (追加)
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
```

Run: `pytest tests/orchestration/signals/test_v2.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add orchestration/signals/ tests/orchestration/signals/
git commit -m "feat(signals): add SignalV2 and SignalPool"
```

---

## Task 2: Aggregator 智能聚合引擎

**Files:**
- Create: `orchestration/signals/aggregator.py`
- Create: `tests/orchestration/signals/test_aggregator.py`

- [ ] **Step 1: 编写 Aggregator 测试**

```python
# tests/orchestration/signals/test_aggregator.py
import pytest
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool
from orchestration.signals.aggregator import Aggregator, AggregatedResult, ConflictStrategy, ConflictHandler

def test_aggregator_basic():
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.BUY, confidence=0.6, weight=0.5, tags=["趋势"]))

    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())

    assert result.action == SignalAction.BUY
    assert result.confidence > 0

def test_aggregator_conflict_recent_wins():
    pool = SignalPool()
    from datetime import timedelta
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.5, weight=0.7,
                       timestamp=datetime.now() - timedelta(hours=2), tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.8, weight=0.5,
                       timestamp=datetime.now(), tags=["技术"]))

    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())
    # 近期信号应该赢
    assert result.action == SignalAction.SELL
```

Run: `pytest tests/orchestration/signals/test_aggregator.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 Aggregator**

```python
# orchestration/signals/aggregator.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from orchestration.signals.v2 import SignalV2, SignalAction

class ConflictHandler(Enum):
    RECENT_WINS = "recent_wins"
    HIGH_CONFIDENCE_WINS = "high_confidence_wins"
    WEIGHTED_VOTING = "weighted_voting"
    DEBATE_MODE = "debate_mode"

@dataclass
class AggregatedResult:
    action: SignalAction
    confidence: float
    reasoning: str
    signals: list[SignalV2]
    conflicts: list[tuple[str, str]]  # (action1, action2)
    metadata: dict = field(default_factory=dict)

class Aggregator:
    def __init__(self, conflict_handler: ConflictHandler = ConflictHandler.RECENT_WINS):
        self.conflict_handler = conflict_handler

    def aggregate(self, signals: list[SignalV2]) -> AggregatedResult:
        if not signals:
            return AggregatedResult(
                action=SignalAction.NEUTRAL,
                confidence=0.0,
                reasoning="无信号",
                signals=[],
                conflicts=[]
            )

        # 检测冲突
        actions = set(s.action for s in signals)
        has_conflict = SignalAction.BUY in actions and SignalAction.SELL in actions

        # 按标签分组
        tag_groups = {}
        for s in signals:
            for tag in s.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(s)

        # 聚合
        if has_conflict:
            final_action, confidence = self._resolve_conflict(signals)
            conflicts = [(SignalAction.BUY.value, SignalAction.SELL.value)]
        else:
            final_action, confidence = self._aggregate_no_conflict(signals)
            conflicts = []

        reasoning = self._build_reasoning(final_action, signals)

        return AggregatedResult(
            action=final_action,
            confidence=confidence,
            reasoning=reasoning,
            signals=signals,
            conflicts=conflicts,
            metadata={"handler": self.conflict_handler.value, "tag_groups": list(tag_groups.keys())}
        )

    def _resolve_conflict(self, signals: list[SignalV2]) -> tuple[SignalAction, float]:
        if self.conflict_handler == ConflictHandler.RECENT_WINS:
            # 按时间排序，取最近的
            sorted_signals = sorted(signals, key=lambda s: s.timestamp, reverse=True)
            winner = sorted_signals[0]
            return winner.action, winner.confidence

        elif self.conflict_handler == ConflictHandler.HIGH_CONFIDENCE_WINS:
            winner = max(signals, key=lambda s: s.confidence * s.weight)
            return winner.action, winner.confidence

        elif self.conflict_handler == ConflictHandler.WEIGHTED_VOTING:
            scores = {SignalAction.BUY: 0.0, SignalAction.SELL: 0.0, SignalAction.HOLD: 0.0, SignalAction.NEUTRAL: 0.0}
            for s in signals:
                scores[s.action] += s.confidence * s.weight
            best = max(scores, key=scores.get)
            return best, scores[best] / len(signals) if signals else 0.0

        elif self.conflict_handler == ConflictHandler.DEBATE_MODE:
            # DEBATE_MODE 返回 HOLD，让后续处理触发辩论
            return SignalAction.HOLD, 0.5

        return SignalAction.NEUTRAL, 0.0

    def _aggregate_no_conflict(self, signals: list[SignalV2]) -> tuple[SignalAction, float]:
        # 非冲突时，加权平均置信度
        total_weight = sum(s.confidence * s.weight for s in signals)
        total_conf = sum(s.confidence for s in signals)
        avg_confidence = total_conf / len(signals) if signals else 0.0

        # 多数投票
        action_counts = {}
        for s in signals:
            action_counts[s.action] = action_counts.get(s.action, 0) + 1
        best_action = max(action_counts, key=action_counts.get)

        return best_action, avg_confidence

    def _build_reasoning(self, action: SignalAction, signals: list[SignalV2]) -> str:
        count = sum(1 for s in signals if s.action == action)
        sources = [s.source for s in signals if s.action == action]
        return f"{action.value.upper()} 信号来自 {', '.join(sources)}，共 {count} 个"
```

Run: `pytest tests/orchestration/signals/test_aggregator.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/signals/aggregator.py tests/orchestration/signals/
git commit -m "feat(signals): add Aggregator with conflict resolution"
```

---

## Task 3: ContextMemory 上下文记忆

**Files:**
- Create: `orchestration/memory.py`
- Create: `tests/orchestration/test_memory.py`

- [ ] **Step 1: 编写 ContextMemory 测试**

```python
# tests/orchestration/test_memory.py
import pytest
from orchestration.memory import ContextMemory, ConversationContext, UserProfile, Turn

def test_context_memory_save():
    mem = ContextMemory()
    ctx = ConversationContext(
        session_id="test-001",
        user_profile=UserProfile(risk_tolerance="medium"),
        asset_focus=["茅台", "宁德时代"],
        history=[]
    )
    mem.save(ctx)
    retrieved = mem.load("test-001")
    assert retrieved is not None
    assert "茅台" in retrieved.asset_focus

def test_preference_learning():
    mem = ContextMemory()
    # 模拟用户多次采纳 SELL 信号
    for _ in range(3):
        mem.record_feedback("user-001", SignalAction.SELL, accepted=True)
    profile = mem.get_user_profile("user-001")
    assert profile.signal_preferences.get(SignalAction.SELL, 0) > 0.5
```

Run: `pytest tests/orchestration/test_memory.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: 实现 ContextMemory**

```python
# orchestration/memory.py
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path
from orchestration.signals.v2 import SignalAction

@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class UserProfile:
    risk_tolerance: str = "medium"  # low, medium, high
    signal_preferences: dict = field(default_factory=dict)  # action -> score

@dataclass
class ConversationContext:
    session_id: str
    history: list[Turn] = field(default_factory=list)
    user_profile: UserProfile = field(default_factory=UserProfile)
    asset_focus: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class ContextMemory:
    def __init__(self, db_path: str = "~/.personax/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                data TEXT,
                created_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                action TEXT,
                accepted INTEGER,
                timestamp TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save(self, ctx: ConversationContext):
        import json
        conn = sqlite3.connect(self.db_path)
        data = {
            "history": [{"role": t.role, "content": t.content, "timestamp": t.timestamp.isoformat()} for t in ctx.history],
            "user_profile": {"risk_tolerance": ctx.user_profile.risk_tolerance, "signal_preferences": ctx.user_profile.signal_preferences},
            "asset_focus": ctx.asset_focus,
        }
        conn.execute(
            "INSERT OR REPLACE INTO conversations (session_id, data, created_at) VALUES (?, ?, ?)",
            (ctx.session_id, json.dumps(data), ctx.created_at)
        )
        conn.commit()
        conn.close()

    def load(self, session_id: str) -> Optional[ConversationContext]:
        import json
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT data FROM conversations WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()
        if not row:
            return None
        data = json.loads(row[0])
        history = [Turn(**t) for t in data.get("history", [])]
        profile = UserProfile(**data.get("user_profile", {}))
        return ConversationContext(
            session_id=session_id,
            history=history,
            user_profile=profile,
            asset_focus=data.get("asset_focus", [])
        )

    def record_feedback(self, session_id: str, action: SignalAction, accepted: bool):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO user_feedback (session_id, action, accepted, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, action.value, int(accepted), datetime.now())
        )
        conn.commit()
        conn.close()

    def get_user_profile(self, session_id: str) -> UserProfile:
        import json
        ctx = self.load(session_id)
        if ctx:
            return ctx.user_profile
        return UserProfile()
```

Run: `pytest tests/orchestration/test_memory.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add orchestration/memory.py tests/orchestration/test_memory.py
git commit -m "feat(memory): add ContextMemory with SQLite persistence"
```

---

## Task 4: OrchestrationEngine 集成

**Files:**
- Modify: `orchestration/engine.py`
- Create: `tests/orchestration/test_engine_v2.py`

- [ ] **Step 1: 编写 Engine 集成测试**

```python
# tests/orchestration/test_engine_v2.py
import pytest
from unittest.mock import MagicMock
from orchestration.engine import OrchestrationEngine, OrchestrationRequest
from orchestration.signals.v2 import SignalAction

def test_engine_with_new_signals():
    engine = OrchestrationEngine()
    # Mock 数据
    request = OrchestrationRequest(
        query="看看茅台",
        df=MagicMock(),
        stock_code="600519"
    )
    # 这个测试验证新流程可以跑通
    # 完整集成测试在 Task 5
```

- [ ] **Step 2: 重构 Engine 使用新模块**

修改 `orchestration/engine.py`:
1. 导入新模块：`from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool`
2. 导入：`from orchestration.signals.aggregator import Aggregator, ConflictHandler`
3. 导入：`from orchestration.memory import ContextMemory`
4. 在 `execute()` 方法中，将策略结果转换为 `SignalV2` 存入 `SignalPool`
5. 使用 `Aggregator` 替代旧的 `SignalAggregator`
6. 将 `aggregated_signal` 改为 `AggregatedResult` 类型

- [ ] **Step 3: 验证测试通过**

```bash
pytest tests/orchestration/test_engine_v2.py -v
pytest tests/orchestration/ -v  # 全部测试
```

- [ ] **Step 4: Commit**

```bash
git add orchestration/engine.py tests/orchestration/test_engine_v2.py
git commit -m "refactor(engine): integrate new signal and memory modules"
```

---

## Task 5: 端到端集成测试

**Files:**
- Create: `tests/orchestration/test_integration_signals.py`

- [ ] **Step 1: 编写端到端测试**

```python
# tests/orchestration/test_integration_signals.py
import pytest
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool
from orchestration.signals.aggregator import Aggregator, ConflictHandler
from orchestration.memory import ContextMemory, ConversationContext

def test_full_pipeline():
    # 1. 收集信号
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["技术"]))

    # 2. 聚合
    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())

    # 3. 记忆
    mem = ContextMemory(db_path=":memory:")
    ctx = ConversationContext(
        session_id="test-full",
        asset_focus=["茅台"]
    )
    mem.save(ctx)

    assert result.conflicts  # 应该有冲突
```

Run: `pytest tests/orchestration/test_integration_signals.py -v`

- [ ] **Step 2: Commit**

```bash
git add tests/orchestration/test_integration_signals.py
git commit -m "test(signals): add end-to-end integration tests"
```

---

## Task 6: 策略扩展（B1/B4 指标）

**Files:**
- Modify: `tools/quant/technical/` 下各指标文件

- [ ] **Step 1: 新增 RSI 指标**

在 `tools/quant/technical/` 下添加 RSI 实现，返回 `SignalV2` 格式

- [ ] **Step 2: 新增 MACD 指标**

同上

- [ ] **Step 3: Commit**

```bash
git add tools/quant/technical/
git commit -m "feat(quant): add RSI and MACD indicators"
```

---

## Task 7: 旧代码清理

**Files:**
- Move: `orchestration/signal_aggregator.py` → `orchestration/legacy/signal_aggregator.py`

- [ ] **Step 1: 确认所有新测试通过后再清理**

```bash
pytest tests/orchestration/ -v
```

- [ ] **Step 2: 移动旧代码**

```bash
mkdir -p orchestration/legacy
mv orchestration/signal_aggregator.py orchestration/legacy/
git add orchestration/legacy/
git commit -m "chore: move legacy signal_aggregator to legacy/"
```

---

## 实施检查清单

- [ ] Task 1: SignalV2 + SignalPool
- [ ] Task 2: Aggregator
- [ ] Task 3: ContextMemory
- [ ] Task 4: Engine 集成
- [ ] Task 5: 端到端测试
- [ ] Task 6: 策略扩展
- [ ] Task 7: 旧代码清理
