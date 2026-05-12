# PersonaX 分析能力增强设计方案

## 背景与目标

现状问题：
- 多策略信号直接相加，缺少置信度、权重、冲突处理
- 每次对话独立，无上下文记忆
- 策略库较薄，实时数据缺失

目标：构建一个**智能信号聚合引擎**，支持置信度评分、上下文记忆、多源实时数据接入。

## 目标架构

```
query → 上下文构建 → 多策略并行分析 → 信号池 → 智能聚合 → 置信度评分 → 最终建议
              ↑                                                                   ↓
         上下文记忆 ←———————————————————————— 历史偏好学习
```

## 核心模块

### 1. SignalV2 — 统一信号格式

```python
@dataclass
class SignalV2:
    source: str              # 策略/指标名称
    action: SignalAction     # BUY / SELL / HOLD / NEUTRAL
    confidence: float         # 置信度 0.0-1.0
    weight: float            # 权重 0.0-1.0
    timestamp: datetime       # 信号产生时间
    metadata: dict            # 原始数据、理由
    tags: list[str]           # 标签：趋势/反转/宏观/技术
```

**SignalAction 枚举：**
- `BUY` — 推荐买入
- `SELL` — 推荐卖出
- `HOLD` — 建议持有
- `NEUTRAL` — 中性/不确定

### 2. SignalPool — 信号收集器

职责：
- 接收所有策略输出的 SignalV2
- 按时间戳+权重排序
- 过滤过期信号（可配置 TTL）
- 检测冲突信号（BUY vs SELL 同时间段）

### 3. Aggregator — 智能聚合引擎

**聚合规则：**
1. 按标签分组（趋势、反转、宏观、技术）
2. 组内加权平均置信度
3. 组间权重由 persona 配置决定
4. 冲突检测：同类标签出现对立信号，触发「信号打架」处理

**打架处理策略（可配置）：**
- `RECENT_WINS` — 近期信号优先
- `HIGH_CONFIDENCE_WINS` — 高置信度优先
- `WEIGHTED_VOTING` — 按权重投票
- `DEBATE_MODE` — 触发辩论流程（输出对立观点）

**最终输出：**
```python
@dataclass
class AggregatedResult:
    action: SignalAction
    confidence: float
    reasoning: str           # 中文理由
    signals: list[SignalV2] # 采纳的信号列表
    conflicts: list[tuple]   # 冲突记录
    metadata: dict           # 聚合元数据
```

### 4. ContextMemory — 上下文记忆

**对话状态：**
```python
@dataclass
class ConversationContext:
    session_id: str
    history: list[Turn]       # 对话历史
    user_profile: UserProfile # 用户偏好
    asset_focus: list[str]   # 关注资产
    risk_tolerance: str      # 风险偏好
```

**偏好学习：**
- 记录用户对不同 signal_action 的反馈（采纳/忽略/反驳）
- 动态调整 persona 对该用户的权重配置
- 持久化到 SQLite

### 5. StrategyExpander — 策略扩展

**新增指标：**
- B3: 动量指标（RSI、MACD）
- B4: 波动率指标（ATR、布林带）
- B5: 成交量异常检测
- 宏观信号：利率曲线、信用利差

**数据源接入（B3 实时数据）：**
- 行情数据：Tushare（已有）
- 新闻舆情：东方财富、新浪财经
- 宏观数据：Wind API / 公开指标

## 实施计划

### Phase 1: SignalV2 + SignalPool
- 新建 `orchestration/signals.py`
- 定义 SignalV2 dataclass
- 实现 SignalPool 收集器
- 迁移现有策略输出到 SignalV2 格式

### Phase 2: Aggregator 重构
- 新建 `orchestration/aggregator.py`
- 实现聚合规则和冲突处理
- 保持向后兼容（适配现有接口）

### Phase 3: ContextMemory
- 新建 `orchestration/memory.py`
- 实现对话状态管理
- SQLite 持久化

### Phase 4: 策略扩展 + 数据源
- 扩展技术指标库
- 接入新闻/舆情数据
- persona 策略配置增强

## 兼容性

- 保持 `OrchestrationEngine` 接口不变
- 新模块通过组合方式集成
- Feature Flag 控制高级功能开关

## 测试策略

- 单元测试：SignalV2、Aggregator 逻辑
- 集成测试：端到端信号流程
- 模拟数据测试冲突处理规则
