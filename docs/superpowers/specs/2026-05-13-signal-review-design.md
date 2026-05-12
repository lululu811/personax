# Signal Review System - 信号回顾与纠错机制

## 背景与目标

现状问题：
- 信号产生后没有跟踪反馈，无法知道准确率
- 指标权重静态固定，不会根据历史表现自动调整
- 没有定期复盘机制

目标：构建一个**异步信号回顾系统**，定期评估信号准确率，动态调整指标权重。

## 设计原则

1. **服务分离** — ReviewService 与 Engine 解耦，独立进程/模块
2. **异步非阻塞** — Engine 发射事件后立即返回，不等待 ReviewService
3. **事件驱动** — 通过 EventBus 解耦，ReviewService 订阅事件
4. **定期回顾** — 每周轻量回顾 + 每月完整复盘

## 目标架构

```
Engine.execute()
    ↓ Fire & Forget (非阻塞)
EventBus.emit(SignalEvent)
    ↓
ReviewService.on_signal(event)
    ↓ 存储
SQLite: signal_history
    ↓ 定时触发
ReviewService.review_weekly() / review_monthly()
    ↓ 评估
权重更新 / 通知
```

## 核心数据结构

### SignalEvent — 信号事件

```python
@dataclass
class SignalEvent:
    timestamp: datetime      # 事件时间
    source: str             # 指标名称：B1策略/RSI/MACD/KDJ
    action: SignalAction   # BUY / SELL
    confidence: float      # 置信度 0.0-1.0
    reason: str            # 信号理由（必须有）
    price: float           # 信号产生时的价格
    asset: str             # 股票代码，如 600519
    tags: list[str]        # 标签：技术/趋势/动量
```

### SignalRecord — 信号记录（SQLite）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| timestamp | TIMESTAMP | 信号时间 |
| source | TEXT | 指标名称 |
| action | TEXT | BUY/SELL |
| confidence | REAL | 置信度 |
| reason | TEXT | 信号理由 |
| price | REAL | 信号时价格 |
| asset | TEXT | 股票代码 |
| tags | TEXT | JSON 标签列表 |
| evaluated | BOOLEAN | 是否已评估 |
| outcome | TEXT | 结果：correct/incorrect/pending |
| outcome_price | REAL | 评估时价格（用于计算涨跌幅）|

### ReviewResult — 回顾结果

```python
@dataclass
class ReviewResult:
    period: str             # weekly/monthly
    start_date: date
    end_date: date
    total_signals: int
    correct: int
    incorrect: int
    pending: int
    accuracy: float        # 准确率
    by_source: dict        # 按指标统计 {source: {correct, total, accuracy}}
    weight_adjustments: dict  # 权重调整 {source: new_weight}
    report: str            # 回顾报告文本
```

## 核心模块

### 1. EventBus — 事件总线

```python
class EventBus:
    """轻量事件总线，支持 Fire & Forget"""

    def emit(self, event_type: str, data: dict):
        """非阻塞发射事件"""
        # 写入队列或直接传递给订阅者
        # 不等待处理结果
        pass

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        pass
```

### 2. ReviewService — 回顾服务

```python
class ReviewService:
    """信号回顾服务"""

    def on_signal(self, event: SignalEvent):
        """接收信号事件，存储到数据库"""
        self.signal_history.add(event)

    def review_weekly(self) -> ReviewResult:
        """每周回顾"""
        # 获取过去一周的信号
        # 用事后价格验证
        # 计算准确率
        # 生成报告
        # 返回权重调整建议

    def review_monthly(self) -> ReviewResult:
        """每月回顾，更全面的分析"""
        pass

    def get_weight_adjustments(self) -> dict:
        """获取当前权重调整建议"""
        pass
```

### 3. SignalHistory — 信号历史

```python
class SignalHistory:
    """信号历史存储"""

    def add(self, event: SignalEvent):
        """添加信号记录"""
        pass

    def get_unevaluated(self) -> list[SignalRecord]:
        """获取未评估的信号"""
        pass

    def mark_evaluated(self, record_id: int, outcome: str, outcome_price: float):
        """标记已评估"""
        pass

    def get_by_period(self, start: date, end: date) -> list[SignalRecord]:
        """按时间段获取信号"""
        pass
```

### 4. Evaluator — 评估器

```python
class Evaluator:
    """用技术指标验证信号对错"""

    def evaluate(self, record: SignalRecord, current_price: float) -> str:
        """评估信号对错

        逻辑：
        - BUY 信号：如果后续 5 日均价 > 信号价格，正确
        - SELL 信号：如果后续 5 日均价 < 信号价格，正确
        - pending: 价格数据未到
        """
        pass

    def get_outcome_price(self, asset: str, signal_timestamp: datetime) -> float:
        """获取信号产生后 N 天的价格"""
        # 接入 Tushare 获取历史价格
        pass
```

### 5. WeightAdjuster — 权重调整

```python
class WeightAdjuster:
    """根据历史表现调整指标权重"""

    def __init__(self, min_weight: float = 0.1, max_weight: float = 1.0):
        self.min_weight = min_weight
        self.max_weight = max_weight

    def compute_adjustments(self, review_result: ReviewResult) -> dict:
        """计算权重调整

        规则：
        - 准确率 > 70%: 权重 +0.1
        - 准确率 50-70%: 权重不变
        - 准确率 < 50%: 权重 -0.1
        - 连续 3 次 < 50%: 标记为低置信度
        """
        pass
```

## Engine 端改动

### Engine 发射事件

```python
class OrchestrationEngine:
    def execute(self, request):
        # ... 原有逻辑 ...

        # 发射信号事件（非阻塞）
        for signal in aggregated_signals:
            event = SignalEvent(
                timestamp=datetime.now(),
                source=signal.source,
                action=signal.action,
                confidence=signal.confidence,
                reason=signal.reason,
                price=self._get_current_price(request.stock_code),
                asset=request.stock_code,
                tags=signal.tags,
            )
            EventBus.emit("signal", event)

        return response
```

## 文件结构

```
orchestration/
├── signals/
│   ├── v2.py              # SignalV2, SignalAction, SignalPool
│   └── aggregator.py       # Aggregator
├── memory.py               # ContextMemory
├── review/                 # 新增
│   ├── __init__.py
│   ├── event_bus.py        # EventBus
│   ├── review_service.py   # ReviewService
│   ├── signal_history.py   # SignalHistory
│   ├── evaluator.py        # Evaluator
│   ├── weight_adjuster.py  # WeightAdjuster
│   └── models.py           # 数据类
└── engine.py               # Engine（发射事件）
```

## 数据库 Schema

```sql
CREATE TABLE signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    price REAL NOT NULL,
    asset TEXT NOT NULL,
    tags TEXT,
    evaluated BOOLEAN DEFAULT FALSE,
    outcome TEXT,
    outcome_price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signal_asset ON signal_history(asset);
CREATE INDEX idx_signal_timestamp ON signal_history(timestamp);
CREATE INDEX idx_signal_evaluated ON signal_history(evaluated);
```

## 触发方式

| 触发 | 时机 |
|------|------|
| **事件触发** | Engine 每产生信号时自动触发 |
| **手动触发** | `python -m orchestration.review.cli weekly/monthly` |
| **定时任务** | cron（后续添加）|

## 依赖

- Tushare（价格数据）
- SQLite（信号历史）
- 现有 ContextMemory（对话记忆）

## 实施顺序

1. EventBus + SignalHistory + models
2. ReviewService 核心（接收事件、存储）
3. Evaluator（评估逻辑）
4. WeightAdjuster（权重调整）
5. CLI 命令
6. Engine 集成（发射事件）
7. 定时任务（后续）
