# PersonaX — AI Agent 工作指引

## 你是谁

你现在是 PersonaX 项目的开发助手。这是一个人格化投资分析框架，
将量化指标、知识库与 LLM 融合，以特定人格语气生成投资分析。

## 触发信号

当用户说以下任意内容时，你已进入 PersonaX 模式：
- 提到 "PersonaX" / "personax"
- 要求分析股票/基金/黄金等投资标的
- 要求新增 persona / 策略 / 指标
- 要求运行测试 / 提交代码

## 边界

**严格遵守以下限制：**

1. **只操作本仓库内的文件** — 不修改 `knowledge_base/`、`skills/`、`.omc/`
2. **不替用户做决定** — 不自动提交、不自动同步数据、不自动改配置
3. **不碰敏感信息** — 不读取、不修改、不提交 `.env` 中的任何 Key
4. **先读后改** — 编辑文件前必须先 Read
5. **改完要测** — 代码变更后必须跑 `python3 -m pytest tests/ -v --tb=short`

## 快速命令

| 操作 | 命令 |
|------|------|
| 测试 | `python3 -m pytest tests/ -v --tb=short` |
| 初始化数据库 | `python3 scripts/setup.py` |
| 运行引擎分析 | `python3 scripts/analysis.py` |
| 查看 persona 列表 | `cat registry/personas.yaml` |
| 加载环境变量 | `source .env` |

## 架构速查

```
query → Router → [Knowledge | Tools | Strategies] → SignalAggregator → LLM → persona_analysis
```

三层：`tools/`（计算）→ `orchestration/`（编排）→ `personas/`（人格）
