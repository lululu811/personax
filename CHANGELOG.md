# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `orchestration/conversation.py` — 多轮对话状态管理（ConversationState / ConversationManager）与诊断引擎（DiagnosisEngine）
- `orchestration/response_generator.py` — LLM 融合生成，支持 5 家后端（DashScope / Anthropic / MiniMax / Kimi / Bailian）
- `tests/test_orchestration/` — 34 个单元测试覆盖对话状态、响应生成、引擎诊断流程
- `personas/persona_loader.py` — 运行时加载 `personality.md` + `overrides.yaml`

### Changed
- `orchestration/engine.py` — 接入知识查询、LLM 生成、多轮对话状态，消除硬编码工具/策略映射
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
