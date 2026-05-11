# PersonaX

> 人格化 AI Agent 框架 — 将量化分析、知识库查询与 LLM 融合，以特定人格语气生成投资分析。

## 触发条件

当用户提出以下类型的需求时，进入 PersonaX Agent 模式：
- "帮我分析 XX 股票" / "看看茅台" / "黄金现在能买吗"
- "用 Z 哥/付鹏/Boss墨 的视角看 XX"
- "跑一下 B1/B2 策略" / "财务排雷"
- "新增 persona" / "新增指标" / "新增策略"

## 边界控制

**这是代码仓库，不是交易终端。**
- 我能做的是：读代码、跑分析脚本、修改配置、写测试
- 我不能做的是：实盘交易、实时监控、自动下单
- 所有分析结果仅供参考，不构成投资建议

**不要替用户做决定。**
- 不自动修改 `.env` 中的 API Key
- 不自动注册 git commit（除非明确要求）
- 不自动同步数据到数据库（除非用户确认）

**不要做超出项目范围的事。**
- 不修改 `knowledge_base/` 下的 Obsidian vault 内容
- 不修改 `skills/` 下的思维模型 skill 文件
- 不修改 `.omc/` 运行时状态

## 架构

三层解耦：
- **Tools** (`tools/`) — 纯计算层，无状态函数
- **Orchestration** (`orchestration/`) — 编排引擎，协调路由、缓存、信号聚合、LLM 生成
- **Personas** (`personas/`) — 人格配置（personality.md + SKILL.md + strategies/）

## 核心链路

```
query → Router → [Knowledge Query | Tool Cache | Data Sync] → Strategies → SignalAggregator → ResponseGenerator(LLM) → persona_analysis
```

## 目录结构

```
├── orchestration/         # 编排层
│   ├── engine.py          # 主引擎
│   ├── router.py          # 路由
│   ├── response_generator.py  # LLM 生成
│   ├── conversation.py    # 多轮对话状态
│   └── ...
├── agent_team/            # Agent 团队 — 多人格头脑风暴与海报生成
│   ├── cli.py             # CLI 入口（brainstorm / deep-dive）
│   ├── core/              # 核心：Agent / Team / Session / Moderator / Reward
│   ├── poster/            # 海报生成（formatter / generator / styles）
│   ├── modes/             # 协作模式：parallel / debate
│   ├── health/            # 健康检查与熔断器
│   └── persistence/       # 反馈持久化（SQLite）
├── tools/                 # 工具层
│   ├── quant/technical/   # 技术指标（B1/B2/六脉神剑等）
│   └── financial_reports/ # 财报分析（五维排雷法、杜邦分析、估值）
├── personas/              # 人格层
│   ├── zettaranc/         # Z 哥 — 超短/情绪/四块砖交易体系
│   ├── fupeng/            # 付鹏 — 宏观策略/杠铃/哑铃
│   ├── boss_mo/           # BOSS墨 — 技术派/次高与分水
│   └── financial_analyst/ # 财务分析师 — 五维排雷/杜邦/估值
├── knowledge/             # 知识层
│   ├── wiki_query.py      # 非向量化 wiki 查询（关键词+标签匹配）
│   └── embeddings.py      # 向量知识库（ChromaDB + DashScope）
├── shared/                # 共享模块
│   ├── config.py          # 注册表配置读取
│   └── env_check.py       # 启动环境校验
├── registry/              # 注册表（YAML 配置）
│   ├── personas.yaml
│   ├── data_sources.yaml
│   └── wiki.yaml          # wiki 公共/个人知识库路径
└── tests/                 # 测试
```

## Agent Team CLI

团队头脑风暴入口，支持多人格并行分析与海报生成：

```bash
# 全明星团队并行分析
python -m agent_team.cli brainstorm --query "看看茅台" --template 全明星

# 技术派辩论模式
python -m agent_team.cli brainstorm --query "宁德时代能买吗" --template 技术派 --mode debate

# 自定义 Agent 组合
python -m agent_team.cli brainstorm --query "黄金走势" --agents zettaranc,boss_mo
```

交互流程：分析 → 评分 → 生成海报（y/n 确认）→ 输出到 `~/.personax/posters/`

## 开发规范

- **新增 persona**: 在 `personas/{name}/` 下创建 personality.md + SKILL.md + strategies/ + overrides.yaml
- **新增指标**: 在 `tools/quant/technical/` 下实现，注册到 `__init__.py`
- **新增策略**: 继承 `BaseStrategy`，实现 `analyze(df) -> StrategySignal`
- **新增工具**: 实现 `run(query, df) -> ToolResult`，注册到 `registry/tools.yaml`
- **新增 wiki**: 配置 `registry/wiki.yaml` 或环境变量 `WIKI_*_DIRS`
- **新增海报风格**: 在 `agent_team/poster/styles.py` 的 `DEFAULT_STYLES` 中添加 `PosterStyle`

## 环境变量

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` / `LLM_API_KEY` | LLM API（通义千问 / Kimi / MiniMax 等）|
| `LLM_PROVIDER` | 提供商：dashscope / kimi / anthropic / minimax / bailian |
| `TUSHARE_TOKEN` | Tushare 数据源 token |
| `TUSHARE_BASE_URL` | Tushare 代理地址（第三方代理时修改）|
| `MINIMAX_API_KEY` | MiniMax WebSearch API Key（Token Plan）|
| `WIKI_PUBLIC_DIRS` | 公共 wiki 路径（逗号分隔）|
| `WIKI_PERSONAL_DIRS` | 个人 wiki 路径（逗号分隔）|

.env 示例见 `.env.example`。

## 测试

```bash
python3 -m pytest tests/ -v --tb=short
```

## 关键设计决策

1. **非向量化 wiki 查询** — 关键词+标签匹配，无需 Embedding，适合个人 Obsidian vault
2. **LLM 优先 + 规则兜底** — 财报分析先用 LLM 提取结构化数据，失败时回退到正则
3. **五维排雷法** — 收入真实性、利润质量、现金流健康、资产负债表、股东回报
4. **模板模式** — 无 LLM API 时，ResponseGenerator 回退到结构化模板输出
5. **WebSearch 降级** — 未配置 `MINIMAX_API_KEY` 时自动跳过 provider，不影响其他功能

## 启动校验

`OrchestrationEngine` 初始化时自动运行 `EnvChecker`，检查：
- LLM API key 是否配置
- Wiki 知识库目录是否可加载
- 数据源 token 是否配置

结果为非阻塞 warning，系统会降级运行。
