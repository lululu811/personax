# PersonaX

> 人格化 AI Agent 投资分析系统 —— 让量化工具拥有「灵魂」

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-114%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-orange.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

PersonaX 是一个**三层解耦**的 AI Agent 框架，将量化计算工具、编排引擎与人格化角色完全分离。你可以像搭积木一样为不同的投资大师（Zettaranc、Financial Analyst 等）配置专属的策略体系、知识库与语言风格，由 LLM 统一融合生成带有人格语气的自然语言回答。

```
用户提问 → 路由层 → [知识查询 | 量化计算 | 策略信号] → LLM 融合 → 人格化回答
```

---

## 核心特性

- **三层解耦架构**：`tools/`（纯计算）↔ `orchestration/`（编排引擎）↔ `personas/`（人格角色）
- **多轮诊断问诊**：3 轮 4 路线（A 持仓诊断 / B 买点确认 / C 逃命判断 / D 长线配置）
- **21 种策略信号**：Zettaranc 战法体系（B1/B2、SB1、少妇战法、三波流 等）
- **BOSS墨交易策略**：涨一段跌一段节奏检测、盈亏比计算（点位>方向）
- **付鹏宏观策略**：哑铃配置、爆金币预警、缩圈抱团检测
- **8 种技术指标**：KDJ、MACD、RSI_3、BBI、Bollinger、ATR、Stochastic
- **财报分析工具链**：自动下载年报/季报、PDF 提取、LLM + 规则双引擎分析
- **知识库向量检索**：基于 ChromaDB + 通义千问 Embedding，支持 Markdown 知识库自动同步
- **多 LLM 后端**：DashScope / MiniMax / Kimi / Bailian / Anthropic 一键切换
- **工具缓存与信号聚合**：避免重复计算，多角色信号冲突自动消解
- **Agent Team 团队头脑风暴**：多人格并行/辩论分析，主持人汇总共识
- **动态权重评分**：用户评分反馈驱动 Agent 权重调整，带探索机制
- **多风格海报生成**：像素风/专业信息图/知识卡片，baoyu 技能驱动

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │   Router (关键词/意图)  │
           └───────────┬───────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌────────────┐ ┌──────────────┐ ┌──────────────┐
│  Knowledge │ │   Tools      │ │  Strategies  │
│  (ChromaDB)│ │(technical/   │ │  (persona)   │
│            │ │ financial)   │ │              │
└─────┬──────┘ └──────┬───────┘ └──────┬───────┘
      │               │                │
      └───────────────┼────────────────┘
                      ▼
           ┌──────────────────┐
           │ SignalAggregator │
           └────────┬─────────┘
                    │
           ┌────────▼────────┐
           │ ResponseGenerator│ ◄── personality.md + LLM
           │   (LLM 融合)     │
           └────────┬────────┘
                    │
           ┌────────▼────────┐
           │ Persona Analysis │
           │  (人格化自然语言)  │
           └──────────────────┘
```

### 三层职责

| 层级 | 目录 | 职责 | 核心类 |
|------|------|------|--------|
| **Tools** | `tools/quant/technical/` `tools/financial_reports/` | 纯计算，无状态，输入 DataFrame 输出 ToolResult | `KDJTool`, `MACDTool`, `FinancialReportTool` |
| **Orchestration** | `orchestration/` | 路由、缓存、聚合、对话状态、LLM 调用 | `OrchestrationEngine`, `ConversationManager`, `ResponseGenerator` |
| **Agent Team** | `agent_team/` | 多人格协作、健康检查、海报生成 | `TeamSession`, `PosterGenerator`, `RewardEngine` |
| **Personas** | `personas/{name}/` | 人格配置、策略集、表达 DNA | `personality.md`, `overrides.yaml`, `strategies/` |

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
# LLM API（至少配置一个）
export DASHSCOPE_API_KEY="your-dashscope-key"        # 通义千问
export ANTHROPIC_API_KEY="your-anthropic-key"        # Claude
export ANTHROPIC_AUTH_TOKEN="your-minimax-token"     # MiniMax
export ANTHROPIC_BASE_URL="https://api.minimax.chat" # MiniMax/Kimi/Bailian base URL

# 数据源
export TUSHARE_TOKEN="your-tushare-token"

# 知识库 Embedding
export DASHSCOPE_API_KEY="your-key"  # 用于 text-embedding-v4
```

### 运行测试

```bash
python3 -m pytest tests/ -v
# 54 passed (agent_team)
```

### 基本用法 —— 技术面分析（Zettaranc）

```python
from orchestration.engine import OrchestrationEngine, OrchestrationRequest
import pandas as pd

# 准备股票数据
df = pd.DataFrame({
    "open": [...], "high": [...], "low": [...],
    "close": [...], "vol": [...]
})

# 执行分析
engine = OrchestrationEngine()
resp = engine.execute(OrchestrationRequest(
    query="Z哥，宁德时代现在能买吗？",
    df=df,
    stock_code="300750.SZ",
))

print(resp.persona_analysis)   # 带 Z 哥语气的自然语言分析
print(resp.aggregated_signal)  # 聚合信号: buy/sell/hold
```

### 财报分析（Financial Analyst）

```python
from tools.financial_reports import FinancialReportTool

# 分析上市公司财报
tool = FinancialReportTool()
result = tool.analyze("600519", include_history=True)

# 查看分析结果
analysis = result["analysis"]
print(analysis.overall_health)   # 综合健康度: 优秀/良好/一般/差
print(analysis.risk_flags)       # 风险标记列表
print(analysis.strengths)        # 核心优势列表
print(analysis.recommendation)   # 建议: 买入/持有/观望/回避

# 查看历史指标趋势
for metrics in result["metrics"]:
    print(f"{metrics.revenue:.0f}万, ROE: {metrics.roe:.1f}%")
```

### 多轮诊断问诊

```python
# Round 1: 系统问"短线还是长线？持仓还是观望？"
resp1 = engine.execute(OrchestrationRequest(
    query="帮我看看这只票", df=df
))
print(resp1.persona_analysis)  # 问诊问题

# Round 2: 用户回答后，系统问路线专属问题
resp2 = engine.execute(OrchestrationRequest(
    query="短线，已持有，仓位20%",
    df=df,
    conversation_id=resp1.conversation_id,
))
print(resp2.diagnosis_route)   # "A" — 持仓诊断路线

# Round 3: 给出诊断结论
resp3 = engine.execute(OrchestrationRequest(
    query="持仓3天，浮盈转浮亏，信号B1",
    df=df,
    conversation_id=resp1.conversation_id,
))
print(resp3.persona_analysis)  # 最终诊断意见
```

### Agent Team 团队头脑风暴

```bash
# 全明星团队并行分析（默认）
python -m agent_team.cli brainstorm --query "看看茅台" --template 全明星

# 技术派辩论模式
python -m agent_team.cli brainstorm --query "宁德时代能买吗" --template 技术派 --mode debate

# 自定义 Agent 组合
python -m agent_team.cli brainstorm --query "黄金走势" --agents zettaranc,boss_mo
```

交互流程：
1. 组建团队 → 并行/辩论分析 → 主持人汇总共识
2. 选择 Agent 深入讨论（可选，最多 3 轮）
3. 为 Agent 打分（1-5 星）
4. 确认生成海报 → 3 种风格并行输出到 `~/.personax/posters/`

```
组建团队: zettaranc, fupeng, boss_mo, financial_analyst (模式: parallel)
--------------------------------------------------

第 1 轮分析结果:

  【zettaranc】
     月线四块砖翻红，周线B1...
     置信度: 85%

  【boss_mo】
     次高已现，分水未突破...
     置信度: 60%

主持人汇总:
   共识: 技术面偏多，但需确认放量
   建议: 关注回调机会，分批建仓

请为参与的 Agent 打分 (1-5星，回车跳过):
  zettaranc: 5
  boss_mo: 4

是否生成海报？ [y/N]: y
生成海报中...（3种风格并行）

  ✓ 像素风高密度信息图: ~/.personax/posters/sess_abc123/infographic-tech/infographic.png
  ✓ 专业手作风格信息图: ~/.personax/posters/sess_abc123/infographic-pro/infographic.png
  ✓ 知识卡片系列: ~/.personax/posters/sess_abc123/image-cards/01-cover-xxx.png

海报保存在: ~/.personax/posters/sess_abc123
```

---

## 项目结构

```
personax/
├── orchestration/           # 编排引擎层
│   ├── engine.py            # 主引擎：路由→工具→策略→LLM融合
│   ├── conversation.py      # 多轮对话状态管理 + 诊断引擎
│   ├── response_generator.py# LLM 调用与 Prompt 构建（5 家后端）
│   ├── router.py            # 查询路由
│   ├── tool_cache.py        # 工具结果缓存
│   └── signal_aggregator.py # 信号冲突聚合
│
├── tools/                   # 工具计算层（纯函数/无状态）
│   ├── quant/technical/     # 技术指标（8 种）
│   │   ├── kdj.py, macd.py, rsi_3.py, bbi.py
│   │   ├── bollinger.py, atr.py, stochastic.py
│   │   └── interface.py     # 注册与发现接口
│   └── financial_reports/   # 财报分析工具
│       ├── downloader.py, extractor.py, analyzer.py
│       └── schemas.py
│
├── personas/                # 人格角色层
│   ├── zettaranc/           # Z 哥人格
│   │   ├── personality.md   # 身份卡 + 表达 DNA
│   │   ├── overrides.yaml   # 阈值与参数覆盖
│   │   ├── SKILL.md         # 问诊流程设计
│   │   └── strategies/      # 21 种策略信号
│   │       ├── b1.py, b2_break.py, five_score.py
│   │       ├── sb1_fake_fall.py, half_release.py
│   │       └── ...
│   └── financial_analyst/   # 财务分析师人格
│
├── quant/                   # 兼容层（向后兼容旧 API）
│   ├── registry.py          # 自动发现 + adapter 桥接
│   └── api.py               # QuantAPI 统一入口
│
├── knowledge/               # 知识库层
│   ├── chunker.py           # Markdown 分块
│   ├── embeddings.py        # Embedding 客户端
│   ├── store.py             # ChromaDB 向量存储
│   ├── query.py             # 语义检索
│   └── sync.py              # 增量同步
│
├── data/                    # 数据层
│   ├── db.py                # DuckDB 本地数据库
│   ├── sync.py              # 多源同步引擎
│   └── sources/             # Tushare 等数据源适配
│
├── agent_team/              # Agent 团队 — 头脑风暴与海报
│   ├── cli.py               # CLI 入口
│   ├── core/                # Agent / Team / Session / Moderator / Reward
│   ├── poster/              # 海报生成
│   ├── modes/               # parallel / debate
│   ├── health/              # 健康检查与熔断器
│   └── persistence/         # 反馈持久化
│
└── tests/                   # 测试
│   ├── test_orchestration/  # 对话 / 响应生成 / 引擎集成
│   ├── test_quant/          # 指标 / 注册表
│   ├── test_knowledge/      # 分块 / Embedding / 检索
│   ├── test_data/           # 数据库 / 同步
│   ├── agent_team/          # Agent Team 测试（54 项）
│   └── test_architecture_integration.py
│
└── scripts/                 # 运维脚本
    ├── setup.py
    ├── sync_data.py
    └── sync_knowledge.py
```

---

## 人格化角色配置

每个角色由三部分定义：

1. **`personality.md`** — 身份卡、表达 DNA（语气/口癖/黑话/禁忌）、心智模型、决策启发式
2. **`overrides.yaml`** — 阈值参数覆盖（如 Z 哥的 B1 触发 J 值 < 13）
3. **`strategies/`** — 专属策略集（自动注册发现）

新增一个角色只需创建 `personas/{name}/` 目录并放入上述文件，Engine 会自动识别。

### 内置角色

| 角色 | 目录 | 专长 | 触发关键词 |
|------|------|------|-----------|
| **付鹏** | `personas/fupeng/` | 宏观策略、风险偏好、资产配置 | "宏观"、"付鹏"、"老付"、"大盘"、"经济" |
| **BOSS墨** | `personas/boss_mo/` | 盘面交易、关键价位、盈亏比、节奏判断 | "BOSS墨"、"黄金"、"原油"、"比特币"、"止损"、"盈亏比" |
| **Zettaranc（Z 哥）** | `personas/zettaranc/` | 技术面、买卖点、仓位管理、心态纪律 | "Z 哥"、"B1"、"少妇战法"、"怎么买" |
| **财务分析师** | `personas/financial_analyst/` | 财报排雷、ROE/毛利率分析、估值判断 | "财报"、"年报"、"ROE"、"基本面" |

#### 付鹏（fupeng）

基于 245 篇 B 站视频转录稿、164 篇书籍文章、16 篇 transcripts 精读、《见证逆潮》全书的深度蒸馏。

**核心心智模型**：
- **三齿轮模型**：生产力 × 生产关系 × 秩序 = 全要素生产率
- **风险偏好 - 资产定价框架**：全社会风险偏好是资产定价核心因子
- **T 字表格 / 资产负债表两端思维**：在通胀的地方挣钱，在通缩的地方花钱
- **缩圈/扩圈理论**：风险偏好收缩时资金从边缘向核心收敛
- **哑铃配置**：确定性资产 + 高风险高回报，不碰中间

**付鹏策略集**（`personas/fupeng/strategies/`）：
- **哑铃策略**（dumbbell）：判断个股位于防御端/进攻端/中间地带
- **爆金币预警**（explosive_gold）：高确定性 + 低波动 + 杠杆堆积 = 闪崩前兆
- **缩圈抱团检测**（shrinking_circle）：判断市场是否处于资金收缩抱团状态

#### BOSS墨（boss_mo）

基于 270+ 个 B 站视频字幕文件（001-287）的深度调研蒸馏。

**核心心智模型**：
- **涨一段跌一段**：市场没有无限涨也没有无限跌，涨完就跌，跌完就涨
- **点位 > 方向**：胜率可以错，只要盈亏比划算，对一次就全赚回来
- **次高与分水**：次高是做空绝佳位置，分水岭是多空分界线
- **刻舟求剑**：历史走势会重演，相似结构预判下一步
- **时间 ↔ 空间互换**：横盘久了就要涨，跌透了就要弹

**BOSS墨策略集**（`personas/boss_mo/strategies/`）：
- **涨一段跌一段节奏检测**（rhythm）：识别高低点→测量当前段→对比历史→判定涨跌阶段
- **盈亏比计算**（risk_reward）：基于次高/前高/前低/右脚自动计算多空盈亏比，2:1 以下不做

#### 财务分析师（financial_analyst）

基于《手把手教你读财报》方法论，专精于上市公司财务报表的深度分析。

**核心能力**：
- **财报排雷**：识别财务造假信号、异常科目、隐藏风险
- **盈利能力分析**：ROE、毛利率、净利率、费用率等核心指标
- **成长性评估**：营收增长、利润增长、现金流增长
- **财务健康度**：资产负债结构、偿债能力、营运效率
- **估值判断**：结合财务数据给出估值区间建议

**五维排雷清单**（分析时逐条检查）：
1. **收入真实性** — 营收增长是否与现金流匹配、应收账款是否异常增长、关联交易占比
2. **利润质量** — 扣非净利润 vs 净利润、非经常性损益占比、毛利率异常波动
3. **现金流健康** — 经营现金流是否为正、经营现金流/净利润比值、自由现金流
4. **资产负债表** — 有息负债率、商誉占比、存货周转天数
5. **股东回报** — ROE 持续性、分红率、股权结构

**分析引擎**：LLM 优先 + 规则兜底双引擎。LLM 可用时，由通义千问基于完整财报文本和人格化 prompt 进行分析；LLM 不可用时，自动降级为规则评分（ROE/毛利率/负债率/成长性四维打分），确保任何情况下都能输出可靠结论。

**输出格式**：
- `overall_health`: 综合健康度（优秀/良好/一般/差）
- `risk_flags`: 风险标记列表
- `strengths`: 核心优势列表
- `concerns`: 关注点列表
- `valuation_comment`: 估值判断
- `recommendation`: 明确建议（买入/持有/观望/回避）

**双角色协作**：当用户同时询问基本面和技术面时（如"这只票基本面怎么样，现在能买吗"），系统会先由 `financial_analyst` 分析财务健康度，再由 `zettaranc` 分析技术信号，最后综合给出建议——基本面决定「买不买」，技术面决定「什么时候买」。

---

## LLM 后端配置

`response_generator.py` 支持以下后端，通过环境变量自动识别：

| 提供商 | 环境变量 | 模型 |
|--------|---------|------|
| DashScope | `DASHSCOPE_API_KEY` | qwen-plus / qwen-max |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-6 |
| MiniMax | `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` | minimax 系列 |
| Kimi | `ANTHROPIC_API_KEY` + `ANTHROPIC_BASE_URL` | kimi 系列 |
| Bailian | `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` | bailian 系列 |

---

## 路线图

- [x] 三层解耦架构（tools / orchestration / personas）
- [x] Zettaranc 21 策略 + 8 技术指标
- [x] 多轮诊断问诊（3 轮 4 路线）
- [x] 多 LLM 后端支持
- [x] 知识库向量检索
- [x] 财报分析工具（FinancialReportTool）
- [x] 付鹏宏观角色 + 3 种宏观策略（哑铃/爆金币/缩圈）
- [x] BOSS墨交易角色 + 2 种交易策略（节奏/盈亏比）
- [x] Agent Team 团队头脑风暴（并行/辩论/海报生成）
- [x] 动态权重评分 + 用户反馈系统
- [x] 多风格海报生成（像素风/信息图/知识卡片）
- [ ] 对话状态持久化（SQLite/DuckDB）
- [ ] 基于 LLM 的意图分类路由
- [ ] 更多人格角色（芒格、Naval 等）
- [ ] 海报风格自定义与扩展

---

## 致谢

- [Tushare](https://tushare.pro) — A 股数据源
- [DashScope](https://dashscope.aliyun.com) — 通义千问 Embedding & LLM
- [ChromaDB](https://chromadb.dev) — 向量数据库

---

## License

CC BY-NC 4.0 — 允许个人/教育/研究用途的自由使用、修改和分发；禁止商业用途。详见 [LICENSE](./LICENSE)
