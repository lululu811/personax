# PersonaX Agent Team 设计文档

> 通用 Agent 团队框架 — 支持多 Persona 协作头脑风暴、动态权重与交互式辩论

## 1. 背景与目标

### 1.1 现状

当前 `OrchestrationEngine` 只支持单 Persona 主分析 + 可选辅助 Persona，所有分析由单一角色完成。

### 1.2 目标

实现**团队头脑风暴模式**：

- 用户提问时，多个 Persona 可以同时参与分析
- 支持三种组队方式：全量召集、智能路由、手动指定
- 支持两种执行模式：快速并行、深度辩论
- 独立的"主持人"角色汇总所有观点
- 用户可以给每个 Persona 打分，系统根据反馈动态调整权重
- 最终输出可生成海报（文本/图片，本期延后实现）

## 2. 核心抽象层

### 2.1 Agent

```python
class Agent:
    """一个可参与协作的智能体。包装 persona，但剥离了业务耦合。"""
    name: str
    role: str
    persona_config: PersonaConfig
    capabilities: list[str]
    circuit_breaker: AgentCircuitBreaker

    async def think(self, query: str, context: AgentContext) -> Thought:
        """独立思考，返回结构化观点。"""

    async def react(self, query: str, others_thoughts: list[Thought]) -> Thought:
        """（辩论模式）看到他人观点后给出反驳或补充。"""
```

**设计意图**：Agent 不是 persona 的别名，而是"可协作的参与者"抽象。未来可接入非 persona Agent（如纯数据 Agent、新闻 Agent）。

### 2.2 Team

```python
class Team:
    """一组 Agent + 协作模式 = 可执行的团队。"""
    name: str
    agents: list[Agent]
    mode: CollaborationMode
    moderator: Moderator

    async def run(self, query: str, stock_df: pd.DataFrame = None) -> TeamResult:
```

### 2.3 Moderator

```python
class Moderator(Agent):
    """主持人 — 特殊 Agent，不参与市场分析，只负责汇总、对比、调和。"""

    async def synthesize(self, thoughts: list[Thought], mode: str) -> Synthesis:
        """汇总所有观点，识别共识与分歧，输出结构化结论。"""
```

## 3. 动态权重与奖赏机制

### 3.1 AgentWeight

```python
class AgentWeight:
    """Agent 在团队中的动态权重。"""
    agent_name: str
    base_weight: float = 1.0
    reputation_score: float = 1.0

    @property
    def effective_weight(self) -> float:
        return self.base_weight * self.reputation_score
```

### 3.2 RewardEngine

```python
class RewardEngine:
    """处理用户反馈，驱动权重动态调整。"""

    def record_feedback(
        self,
        team_run_id: str,
        agent_name: str,
        user_score: float,          # -1.0 ~ +1.0
        feedback_text: str = "",
        query_tags: list[str] = None,
    ):
        """记录用户反馈，更新 Agent 权重。"""

    def get_personalized_team(
        self,
        query: str,
        available_agents: list[str],
        top_k: int = 3,
    ) -> list[AgentWeight]:
        """根据用户历史偏好 + 问题类型，智能组队。"""
```

### 3.3 关键设计决策

- **按场景记权重**：按问题标签（技术面、宏观、财报、短线、长线...）分别记分
- **显式 + 隐式反馈**：用户主动点赞/点踩（显式），用户最终采纳了哪个 Agent 建议（隐式）
- **探索 vs 利用**：保留 10-20% 概率让低权重但相关的 Agent 参与，避免信息茧房

## 4. 多轮交互式辩论流程

### 4.1 Session 状态机

```
IDLE -> BRAINSTORMING -> REVIEWING -> DEBATING -> REVIEWING -> ... -> CLOSED
```

### 4.2 TeamSession

```python
class TeamSession:
    session_id: str
    status: SessionStatus
    team: Team
    rounds: list[Round]
    current_deep_dive: str = None

    MAX_TEAM_ROUNDS = 3
    MAX_DEEP_DIVE_ROUNDS = 3
    MAX_TOTAL_TURNS = 10

    async def start_brainstorm(self, query: str) -> Round:
        """第一阶段：所有 Agent 并行给出初始观点。"""

    async def start_deep_dive(self, agent_name: str, user_challenge: str) -> DebateRound:
        """第二阶段：和指定 Agent 深入辩论（用户驱动）。"""

    async def stop_debate(self) -> None:
        """用户决定结束辩论，回到 reviewing 状态。"""

    async def close(self, user_scores: dict[str, float]) -> TeamResult:
        """用户结束并打分。"""
```

### 4.3 交互流程示例

```
用户: "帮我看看茅台"

系统: 【团队头脑风暴中...】
      ├─ Z哥: "月线四块砖刚翻红..."
      ├─ 财务分析师: "ROE 连续5年>20%..."
      ├─ 付鹏: "宏观层面消费复苏缓慢..."
      └─ BOSS墨: "1800 是次高..."

      【主持人汇总】共识、分歧、建议...

用户: "BOSS墨你说的次高，具体怎么看？"
      → 进入和 BOSS墨 的 1v1 辩论

系统: 【BOSS墨回应】...

用户: "那如果缩量跌破呢？"
      → 第 2 轮

用户: "行了，明白了"
      → 用户主动结束辩论，回到 review

用户: "结束吧"
      → 进入评分

系统: 请为 Agent 打分（1-5星，可跳过）...
      保存反馈，更新权重...
```

### 4.4 关键交互原则

- **用户是节奏控制器**：系统只在用户明确说"够了"或"结束"时才推进
- **辩论是 1v1**：用户一次只和一个 Agent 深入
- **辩论轮次上限**：单个 Agent 最多 3 轮
- **评分可选**：用户可以给部分 Agent 打分

## 5. 协作模式

### 5.1 并行模式（ParallelExecutor）

```python
class ParallelExecutor:
    async def execute(self, team: Team, query: str, context: AgentContext) -> list[Thought]:
        tasks = [
            asyncio.wait_for(agent.think(query, context), timeout=30.0)
            for agent in team.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 单个失败不影响其他人
```

### 5.2 辩论模式（DebateExecutor）

```python
class DebateExecutor:
    async def execute(self, team: Team, query: str, context: AgentContext) -> list[Thought]:
        # Round 1: 并行初始思考
        initial_thoughts = await asyncio.gather(*[agent.think(query, context) for agent in team.agents])

        # Round 2: 并行反驳
        rebuttal_tasks = []
        for agent in team.agents:
            others = [t for t in initial_thoughts if t.agent_name != agent.name]
            rebuttal_tasks.append(agent.react(query, others))
        rebuttal_thoughts = await asyncio.gather(*rebuttal_tasks)

        return initial_thoughts + rebuttal_thoughts
```

### 5.3 交叉辩论模式（CrossfireExecutor）— 后期实现

两个 Agent 直接对线，用户作为裁判。

## 6. 数据持久化

SQLite 存储，表结构：

```sql
-- team_sessions: 会话记录
CREATE TABLE team_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    query TEXT,
    team_template TEXT,
    status TEXT,
    created_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- round_results: 每轮结果
CREATE TABLE round_results (
    round_id TEXT PRIMARY KEY,
    session_id TEXT,
    round_type TEXT,
    agent_name TEXT,
    content TEXT,
    confidence REAL,
    timestamp TIMESTAMP
);

-- debate_rounds: 辩论记录
CREATE TABLE debate_rounds (
    debate_id TEXT PRIMARY KEY,
    session_id TEXT,
    agent_name TEXT,
    user_challenge TEXT,
    agent_response TEXT,
    round_num INTEGER,
    timestamp TIMESTAMP
);

-- feedback_scores: 用户反馈
CREATE TABLE feedback_scores (
    feedback_id TEXT PRIMARY KEY,
    session_id TEXT,
    agent_name TEXT,
    user_score REAL,
    feedback_text TEXT,
    query_tags TEXT,  -- JSON array
    timestamp TIMESTAMP
);

-- agent_reputation: Agent 声望
CREATE TABLE agent_reputation (
    agent_name TEXT,
    tag TEXT,
    cumulative_score REAL,
    sample_count INTEGER,
    avg_score REAL,
    last_updated TIMESTAMP,
    PRIMARY KEY (agent_name, tag)
);
```

## 7. API 接口设计

### 7.1 启动头脑风暴

```http
POST /api/v1/team/brainstorm
Content-Type: application/json

{
    "query": "帮我看看茅台",
    "template": "全明星",
    "custom_agents": ["zettaranc", "boss_mo"],
    "stock_code": "600519",
    "mode": "parallel"
}
```

```http
HTTP/1.1 200 OK

{
    "session_id": "sess_xxx",
    "status": "reviewing",
    "round": {
        "round_num": 1,
        "agent_thoughts": [
            {"agent": "zettaranc", "content": "...", "confidence": 0.75}
        ],
        "moderator_summary": "..."
    }
}
```

### 7.2 深度辩论

```http
POST /api/v1/team/debate
Content-Type: application/json

{
    "session_id": "sess_xxx",
    "agent_name": "boss_mo",
    "user_challenge": "你说的次高具体怎么看？"
}
```

```http
HTTP/1.1 200 OK

{
    "debate_round": 2,
    "agent_response": "...",
    "max_rounds_reached": false
}
```

### 7.3 结束并评分

```http
POST /api/v1/team/close
Content-Type: application/json

{
    "session_id": "sess_xxx",
    "scores": {
        "zettaranc": 4.5,
        "boss_mo": 5.0
    }
}
```

## 8. 与现有系统集成

### 8.1 目录结构

```
agent_team/              # 新增
  ├── core/
  │   ├── agent.py
  │   ├── team.py
  │   ├── moderator.py
  │   ├── weight.py
  │   ├── reward.py
  │   ├── session.py
  │   └── health.py
  ├── modes/
  │   ├── parallel.py
  │   ├── debate.py
  │   └── crossfire.py
  ├── persistence/
  │   └── feedback_store.py
  └── poster/            # 延后实现
      ├── text.py
      └── image.py

api/v1/team.py           # 新增 API
```

### 8.2 复用策略

- **Agent.think()**：直接复用 `ResponseGenerator.generate()`
- **工具计算**：`TeamSession._prepare_context()` 预计算一次，所有 Agent 共享
- **Persona 加载**：复用 `personas.persona_loader.load_persona()`
- **LLM 调用**：复用现有的多 provider 支持（DashScope/Anthropic/MiniMax 等）

### 8.3 入口判断

`api/v1/chat.py` 中根据请求参数决定路由：

```python
if request.mode == "team":
    return await team_handler.handle(request)
else:
    return await chat_handler.handle(request)  # 现有逻辑
```

## 9. 核心实现机制

### 9.1 Agent 包装层

Agent 不复写 LLM 调用，而是包装现有的 `ResponseGenerator`：

```python
class Agent:
    def __init__(self, name: str, persona_config: PersonaConfig):
        self.name = name
        self.persona_config = persona_config
        self.generator = ResponseGenerator()

    async def think(self, query: str, context: AgentContext) -> Thought:
        analysis = self.generator.generate(
            query=query,
            persona_config=self.persona_config,
            context=GenerationContext(...),
        )
        return Thought(...)
```

### 9.2 并行执行

```python
async def execute(team, query, context):
    tasks = [
        asyncio.wait_for(agent.think(query, context), timeout=30.0)
        for agent in team.agents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 单个失败返回降级结果，不影响其他人
```

### 9.3 工具数据共享

```python
async def _prepare_context(self, query: str, df: pd.DataFrame) -> AgentContext:
    """预计算工具数据，所有 Agent 共享。"""
    tool_results = self._compute_tools(query, df)
    strategy_results = self._run_strategies(query, df, tool_results)
    knowledge_snippets = self._query_knowledge(query)
    return AgentContext(
        tool_results=tool_results,
        strategy_results=strategy_results,
        knowledge_snippets=knowledge_snippets,
    )
```

## 10. 容错与防死循环

### 10.1 多层超时

| 层级 | 超时时间 | 降级行为 |
|------|---------|---------|
| LLM 调用 | 25s | 返回降级输出 |
| 工具计算 | 15s | 跳过该工具 |
| Agent.think() | 35s | 熔断 |
| 团队一轮 | 60s | 部分结果 |
| 深度辩论单轮 | 40s | 提示用户 |
| 总会话 | 300s | 强制结束 |

### 10.2 健康检查

```python
class AgentHealthChecker:
    def check_thought(self, thought: Thought) -> HealthResult:
        issues = []
        if len(thought.content.strip()) < 20:
            issues.append("输出过短")
        if self._is_repetitive(thought):
            issues.append("输出重复")
        if self._is_self_contradictory(thought):
            issues.append("自我矛盾")
        return HealthResult(is_healthy=len(issues) == 0, issues=issues)
```

### 10.3 熔断器

```python
class AgentCircuitBreaker:
    def __init__(self, agent_name: str):
        self.failure_count = 0
        self.state = "closed"  # closed / open / half_open

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= 3:
            self.state = "open"

    def can_execute(self) -> bool:
        if self.state == "open":
            if time.time() - self.last_failure_time > 120:
                self.state = "half_open"
                return True
            return False
        return True
```

### 10.4 死循环检测

- **用户循环**：连续 3 次问"为什么"或重复提问 → 提示结束
- **辩论循环**：Agent A/B 反复看多/看空（ABABAB）→ 提示结束
- **轮次上限**：总会话最多 10 次交互，深度辩论最多 3 轮

## 11. 延后项

| 功能 | 原因 |
|------|------|
| 海报生成（文本/图片） | 需要 UI 设计，本期聚焦核心机制 |
| Token 消耗硬限制 | 10 万 token 预算不足，先改为监控模式，后续根据实际用量调整 |
| WebSocket 流式推送 | 体验优化，API 模式先跑通 |
| 交叉辩论（Agent 间对线） | 交互复杂度高，后续迭代 |

## 12. 团队模板预设

```python
TEAM_TEMPLATES = {
    "全明星": ["zettaranc", "fupeng", "boss_mo", "financial_analyst"],
    "技术派": ["zettaranc", "boss_mo"],
    "基本面派": ["financial_analyst", "fupeng"],
    "快问快答": "auto",  # 只选权重最高的 2 个
}
```

## 13. 监控指标

```python
class TeamMetrics:
    """记录关键指标。"""
    # agent_timeout: Agent 超时次数
    # agent_failure: Agent 失败次数
    # loop_detected: 死循环检测次数
    # session_aborted: 会话被强制终止次数
    # avg_response_time: 平均响应时间
```
