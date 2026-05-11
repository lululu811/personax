# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `agent_team/` — Agent 团队头脑风暴框架
  - `core/` — `Agent`, `Team`, `Moderator`, `TeamSession`, `RewardEngine`
  - `modes/` — `ParallelExecutor`（并行分析）与 `DebateExecutor`（辩论模式）
  - `health/` — `AgentHealthChecker`（输出质量检查）与 `AgentCircuitBreaker`（熔断器）
  - `persistence/` — `FeedbackStore`（SQLite 反馈与声誉持久化）
  - `poster/` — 多风格海报生成模块
    - `styles.py` — `PosterStyle` 注册表，3 种默认风格（像素信息图/专业信息图/知识卡片）
    - `formatter.py` — `InfographicFormatter` + `ImageCardsFormatter`
    - `generator.py` — `PosterGenerator`，并行调用 baoyu 技能生成海报
  - `cli.py` — Click CLI：`brainstorm` 命令 + 交互式 deep-dive + 海报确认
- `agent_team/core/models.py` — `TeamResult.poster_paths` 字段
- `tests/agent_team/` — 54 个 pytest 测试覆盖 Agent Team 全部功能
- `personas/fupeng/` — 付鹏宏观人格（`personality.md` + `SKILL.md` + `overrides.yaml`）
- `personas/fupeng/strategies/` — 3 种付鹏宏观策略：
  - `dumbbell.py` — 哑铃配置（防御端/进攻端/中间地带）
  - `explosive_gold.py` — 爆金币预警（高确定性+低波动+杠杆堆积=闪崩前兆）
  - `shrinking_circle.py` — 缩圈抱团检测（资金收缩抱团判断）
- `personas/boss_mo/` — BOSS墨交易人格（`personality.md` + `SKILL.md` + `overrides.yaml`）
- `personas/boss_mo/strategies/` — 2 种 BOSS墨交易策略：
  - `rhythm.py` — 涨一段跌一段节奏检测（识别高低点→对比历史→判定涨跌阶段）
  - `risk_reward.py` — 盈亏比计算（基于次高/前高/前低/脚位自动计算多空盈亏比）
- `registry/wiki.yaml` — fupeng + boss_mo 个人知识库注册
- `orchestration/engine.py` — 多 persona 策略适配层（`_adapt_fupeng_signal` + `_adapt_boss_mo_signal`），将自定义结果类型统一为 `StrategySignal`
- `orchestration/conversation.py` — 多轮对话状态管理（ConversationState / ConversationManager）与诊断引擎（DiagnosisEngine）
- `orchestration/response_generator.py` — LLM 融合生成，支持 5 家后端（DashScope / Anthropic / MiniMax / Kimi / Bailian）
- `tests/test_orchestration/` — 34 个单元测试覆盖对话状态、响应生成、引擎诊断流程
- `personas/persona_loader.py` — 运行时加载 `personality.md` + `overrides.yaml`

### Changed
- `orchestration/router.py` — 新增付鹏/BOSS墨关键词路由（宏观/大盘/经济→fupeng，黄金/原油/比特币/止损→boss_mo）
- `orchestration/engine.py` — 接入知识查询、LLM 生成、多轮对话状态，消除硬编码工具/策略映射；新增多 persona 策略动态加载与信号适配
- `quant/registry.py` — 改为 adapter 层，自动桥接 `tools/quant/technical/` 新架构与旧 API

### Removed
- `quant/indicators/zettaranc/` 旧目录 — 策略已迁移至 `personas/zettaranc/strategies/`
- `quant/indicators/macd.py`, `rsi.py` — 由 `tools/quant/technical/` 统一提供

## [0.5.0] - 2025-05

### Added
- `tools/financial_reports/` — 财报分析工具链（下载器 / PDF 提取器 / 规则分析器）
- `personas/financial_analyst/` — 财务分析师人格角色
- `orchestration/engine.py` — 集成 financial report 工具，支持财报关键词路由

## [0.4.0] - 2025-04

### Added
- `orchestration/` 编排引擎层 — Router、ToolCache、SignalAggregator、Engine
- `personas/zettaranc/strategies/` — 21 种策略信号（B1/B2/SB1/五维评分/少妇战法/三波流 等）
- `tools/quant/technical/` — 8 种技术指标（KDJ、MACD、RSI_3、BBI、Bollinger、ATR、Stochastic）
- `tools/quant/technical/interface.py` — `@register_tool` 装饰器与自动发现机制
- 三层架构解耦：Tools（纯计算）↔ Orchestration（编排）↔ Personas（人格）

### Changed
- 策略与指标从 `quant/` 迁移至 `tools/quant/technical/` 和 `personas/zettaranc/strategies/`
- `quant/` 保留为兼容层，通过 `registry.py` adapter 桥接新旧接口

## [0.3.0] - 2025-03

### Added
- Zettaranc 复合指标体系 v2.x（知识挖掘扩展）
  - v2.0: 4 种复合指标
  - v2.1: 4 种新复合指标
  - v2.2: 5 种复合信号
  - v2.3: 4 种知识挖掘指标
- `personas/zettaranc/personality.md` — 人格身份卡与表达 DNA
- `personas/zettaranc/SKILL.md` — 问诊流程设计文档
- `personas/zettaranc/overrides.yaml` — 阈值参数覆盖

## [0.2.0] - 2025-02

### Added
- `knowledge/` — 知识库层（Markdown chunker、Embedding、ChromaDB 存储、语义检索、增量同步）
- `data/` — 数据层（DuckDB 本地数据库、Tushare 数据源、多源同步引擎）
- `shared/config.py` — 统一配置加载
- 用户资产表：watchlist、holdings、trades

## [0.1.0] - 2025-01

### Added
- 项目骨架与注册表配置
- `quant/` 量化层：指标注册表、MA/MACD/RSI 核心指标、统一 API（分析 + 回测）
- `bridge/` — CLI 入口（知识同步、量化分析）
- `scripts/` —  setup、数据同步、知识同步脚本
- 集成测试覆盖所有层级
