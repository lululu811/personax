# PersonaX

> 人格化 AI Agent 框架 — 将量化分析、知识库查询与 LLM 融合，以特定人格语气生成投资分析。

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
├── tools/                 # 工具层
│   ├── quant/technical/   # 技术指标（B1/B2/六脉神剑等）
│   └── financial_reports/ # 财报分析（五维排雷法、杜邦分析、估值）
├── personas/              # 人格层
│   ├── zettaranc/         # Z 哥 — 超短/情绪/四块砖交易体系
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

## 开发规范

- **新增 persona**: 在 `personas/{name}/` 下创建 personality.md + SKILL.md + strategies/
- **新增指标**: 在 `tools/quant/technical/` 下实现，注册到 `__init__.py`
- **新增策略**: 继承 `BaseStrategy`，实现 `analyze(df) -> StrategySignal`
- **新增工具**: 实现 `run(query, df) -> ToolResult`，注册到 `registry/tools.yaml`
- **新增 wiki**: 配置 `registry/wiki.yaml` 或环境变量 `WIKI_*_DIRS`

## 环境变量

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` / `LLM_API_KEY` | LLM API（通义千问 / Kimi / MiniMax 等）|
| `LLM_PROVIDER` | 提供商：dashscope / kimi / anthropic / minimax / bailian |
| `TUSHARE_TOKEN` | Tushare 数据源 token |
| `TUSHARE_BASE_URL` | Tushare 代理地址（第三方代理时修改）|
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

## 启动校验

`OrchestrationEngine` 初始化时自动运行 `EnvChecker`，检查：
- LLM API key 是否配置
- Wiki 知识库目录是否可加载
- 数据源 token 是否配置

结果为非阻塞 warning，系统会降级运行。
