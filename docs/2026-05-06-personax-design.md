# PersonaX 架构设计文档

> 版本：v1.0
> 日期：2026-05-06
> 状态：设计中

---

## 1. 项目概述

### 1.1 项目名称

**PersonaX**（千面）

### 1.2 项目定位

PersonaX 是一个**分层解耦的角色化 AI Agent 框架**，核心能力是将真实人物的思维模型通过蒸馏方式提取，封装为可复用的数字人格。每个数字人格具备：

- **人格化对话**：以目标人物的语气、节奏、思维框架回应用户
- **知识库检索**：基于向量语义搜索的动态知识库
- **量化分析**：面向本地数据库的金融数据分析和回测能力

### 1.3 核心理念

**"铸魂"**——不是简单模仿一个人的说话方式，而是提炼其最核心的思维操作系统（心智模型 + 决策启发式 + 表达 DNA），并赋予 AI 持续学习和演化的能力。

### 1.4 目标用户

- 个人投资者：希望获得特定投资大师的"数字分身"作为思维顾问
- 研究团队：需要快速构建和切换多个专家视角进行分析
- 知识工作者：希望将自己的思维模型沉淀为可复用的 AI 助手

---

## 2. 架构总览

### 2.1 分层架构

PersonaX 采用 **四层 + 注册中心** 的架构：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Registry（注册中心）                           │
│  ┌─────────────┐ ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ personas    │ │ knowledge_bases │ │data_sources │ │ indicators  │   │
│  │ .yaml       │ │    .yaml        │ │   .yaml     │ │  .yaml      │   │
│  └─────────────┘ └─────────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   人格层     │  │   知识层     │  │   数据层     │  │   量化层     │   │
│  │  Persona    │  │  Knowledge  │  │    Data     │  │    Quant    │   │
│  │             │  │             │  │             │  │             │   │
│  │ SKILL.md    │  │ ChromaDB    │  │  DuckDB     │  │  指标计算    │   │
│  │ + 角色配置   │  │ + 通义千问   │  │ + 同步引擎   │  │  + 回测     │   │
│  │             │  │             │  │             │  │             │   │
│  │ 初始化时读   │  │ 查询时读     │  │ 同步时读     │  │ 计算时读     │   │
│  │ personas    │  │ knowledge_  │  │ data_sources│  │ indicators  │   │
│  │ .yaml       │  │ bases.yaml  │  │  .yaml      │  │  .yaml      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│  用户提问 → 人格层路由 → 知识查询 / 量化分析 → LLM 融合生成回答          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**分层原则：**

- 每一层只依赖 Registry 和下一层（通过标准接口）
- 层与层之间通过**数据契约**（标准格式）通信，不直接调用实现细节
- 每层内部可以独立开发、独立测试、独立部署

### 2.2 注册中心（Registry）

Registry 是 PersonaX 的**配置驱动核心**。所有扩展（新角色、新知识库、新数据源、新指标）都通过修改 Registry 配置完成，**无需修改核心代码**。

---

## 3. 人格层（Persona Layer）

### 3.1 职责

定义 AI Agent 的"人格"——包括角色身份、表达 DNA、决策框架、交互规则。

### 3.2 设计原则

- **纯静态配置**：所有人格定义都是 Markdown/YAML 文件，不含代码
- **模板继承**：支持基础模板 + 个性覆盖的机制，避免重复
- **能力声明**：每个角色在 Registry 中声明自己可访问的知识库、数据源、功能开关

### 3.3 目录结构

```
personas/
├── zettaranc/                        # Z哥角色
│   ├── SKILL.md                      # Claude Code 入口（系统提示词）
│   ├── personality.md                # 个性覆盖（表达 DNA、口头禅、决策框架）
│   └── overrides.yaml                # 配置覆盖（可选）
│
├── qishui/                           # 啟水角色
│   ├── SKILL.md
│   ├── personality.md
│   └── overrides.yaml
│
└── fupeng/                           # 傅鹏角色（示例）
    └── ...
```

### 3.4 关键文件

#### SKILL.md

Claude Code 的 Skill 入口文件，包含：

- 系统提示词（角色定义）
- 可用工具声明（知识查询、量化分析等）
- 交互规则（如"遇到个股问题先进入多轮问诊"）

#### personality.md

角色的个性覆盖文件，定义：

- **表达 DNA**：语气（急促/沉稳）、节奏（短句/长句）、口头禅、修辞习惯
- **决策框架**：核心心智模型、决策启发式、边界条件
- **价值观**：对风险、收益、概率的态度

#### overrides.yaml

可选的配置覆盖，用于微调角色的默认行为。

### 3.5 人格注册表

```yaml
# registry/personas.yaml
personas:
  zettaranc:
    name: "Z哥"
    display_name: "万千"
    base_template: "investor_advisor"
    description: "基于Z哥直播/课程提炼的投资思维模型"
    knowledge_bases: ["zettaranc", "common"]
    data_sources: ["tushare"]
    features:
      quant_enabled: true
      multi_turn_diagnosis: true
      web_search: false
    quant_overrides:
      default_indicators: ["MA", "MACD", "RSI", "FUND_FLOW"]
```

### 3.6 扩展方式

新增角色 = `personas.yaml` 添加配置 + 新建 `personas/<name>/` 目录。

---

## 4. 知识层（Knowledge Layer）

### 4.1 职责

管理角色的专属知识库，提供基于语义向量的检索能力。

### 4.2 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 向量数据库 | ChromaDB | 纯本地、零配置、Python 原生 |
| Embedding 模型 | 通义千问 text-embedding-v3 | 中文效果优秀、国内直连稳定 |
| 文档切分 | Markdown-aware | 保留标题层级，语义完整 |

### 4.3 核心模块

#### store.py —— ChromaDB 封装

支持多 collection（每个知识库独立 collection），提供标准 CRUD 和语义查询接口。

#### query.py —— 查询路由

```python
def query(question: str, persona: str, n_results: int = 5) -> str:
    """
    1. 从 Registry 读取该角色可访问的知识库列表
    2. 多 collection 联合查询
    3. 合并、去重、格式化返回
    """
```

#### chunker.py —— Markdown 切分

按标题层级切分，每个 chunk 保留完整标题路径。

#### sync.py —— 同步引擎

增量同步：扫描 Obsidian vault → 计算文件 hash → 只处理变更文件 → 切分 → Embedding → 入库。

#### embeddings.py —— 通义千问 Embedding 封装

支持 API 调用和错误处理，可切换模型版本。

### 4.4 知识库注册表

```yaml
# registry/knowledge_bases.yaml
knowledge_bases:
  zettaranc:
    name: "Z哥投资框架"
    vault_path: "/home/chenlei/001_AI/knowledge_base/zettaranc-knowledge"
    collection: "zettaranc"
    embedding:
      provider: "dashscope"
      model: "text-embedding-v3"
    chunker:
      strategy: "heading"
      max_chunk_size: 1000
    sync:
      trigger: "manual"
```

### 4.5 目录结构

```
knowledge/
├── __init__.py
├── config.yaml
├── models.py
├── embeddings.py
├── chunker.py
├── store.py
├── query.py
├── sync.py
└── vector_store/
    ├── zettaranc/
    ├── qishui/
    └── common/
```

### 4.6 扩展方式

新增知识库 = `knowledge_bases.yaml` 添加配置 + 指定 vault 路径。

---

## 5. 数据层（Data Layer）

### 5.1 职责

从外部数据源拉取金融数据，存储到本地数据库，为量化层提供统一、离线可用的数据服务。

### 5.2 核心设计原则

**量化层 100% 面向本地数据库开发，完全不感知外部 API。**

### 5.3 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 本地数据库 | DuckDB | 列式分析型数据库，OLAP 性能优秀，单文件零配置 |
| 数据源抽象 | Python ABC | 统一接口，支持多源 fallback |

### 5.4 数据库 Schema

#### 股票基本信息表

```sql
CREATE TABLE stocks (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    industry VARCHAR(50),
    market VARCHAR(10),
    list_date DATE,
    is_active BOOLEAN DEFAULT true
);
```

#### 日线行情表（核心表）

```sql
CREATE TABLE daily_prices (
    code VARCHAR(20),
    trade_date DATE,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    amount DECIMAL(20,4),
    change_pct DECIMAL(8,4),
    turnover_rate DECIMAL(8,4),
    source VARCHAR(20),
    PRIMARY KEY (code, trade_date)
);
```

#### 资金流表

```sql
CREATE TABLE fund_flow (
    code VARCHAR(20),
    trade_date DATE,
    main_in DECIMAL(20,4),
    main_out DECIMAL(20,4),
    main_net DECIMAL(20,4),
    retail_in DECIMAL(20,4),
    retail_out DECIMAL(20,4),
    retail_net DECIMAL(20,4),
    total_amount DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, trade_date)
);
```

#### 财务数据表

```sql
CREATE TABLE financials (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    eps DECIMAL(12,4),
    bvps DECIMAL(12,4),
    pe DECIMAL(12,4),
    pb DECIMAL(12,4),
    roe DECIMAL(8,4),
    revenue DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);
```

#### 同步日志表

```sql
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR(50),
    code VARCHAR(20),
    data_source VARCHAR(20),
    start_date DATE,
    end_date DATE,
    records_count INTEGER,
    status VARCHAR(20),
    synced_at TIMESTAMP DEFAULT now()
);
```

### 5.5 核心模块

#### db.py —— DuckDB 封装

提供标准查询接口：

```python
class Database:
    def get_daily(self, code: str, start: str = None, end: str = None) -> pd.DataFrame: ...
    def get_fund_flow(self, code: str, days: int = 30) -> pd.DataFrame: ...
    def check_data_gaps(self, code: str, table: str) -> list[tuple]: ...
    def get_last_trade_date(self, code: str, table: str) -> str: ...
```

#### sources/base.py —— 数据源抽象基类

```python
class DataSource(ABC):
    name: str
    priority: int
    
    @abstractmethod
    def get_daily(self, code: str, start: str, end: str) -> pd.DataFrame: ...
    @abstractmethod
    def get_fund_flow(self, code: str, start: str, end: str) -> pd.DataFrame: ...
```

#### sources/tushare_source.py —— Tushare 实现

```python
class TushareSource(DataSource):
    name = "tushare"
    priority = 1
    
    def __init__(self):
        import tushare as ts
        ts.set_token(os.environ["TUSHARE_TOKEN"])
        self.pro = ts.pro_api()
        self.pro._DataApi__http_url = "http://tsy.xiaodefa.cn"
```

#### sync.py —— 同步引擎

```python
class SyncEngine:
    def sync_stock(self, code: str, tables: list[str] = None):
        """
        1. 检查本地最新日期
        2. 按 Registry 优先级尝试各数据源
        3. 成功后写入 DuckDB，失败则 fallback 到下一个源
        """
```

### 5.6 数据源注册表

```yaml
# registry/data_sources.yaml
data_sources:
  tushare:
    name: "Tushare"
    type: "api"
    priority: 1
    enabled: true
    module: "data.sources.tushare_source"
    class: "TushareSource"
    config:
      base_url: "http://tsy.xiaodefa.cn"
      token_env: "TUSHARE_TOKEN"
    supported_tables:
      - daily_prices
      - fund_flow
      - financials
      - stocks
```

### 5.7 目录结构

```
data/
├── __init__.py
├── registry.py
├── db.py
├── schema.sql
├── models.py
├── sync.py
├── sources/
│   ├── __init__.py
│   ├── base.py
│   ├── tushare_source.py
│   └── akshare_source.py
└── cache/
    └── market.duckdb
```

### 5.8 扩展方式

新增数据源 = `data_sources.yaml` 添加配置 + 实现 `DataSource` 子类。

---

## 6. 量化层（Quant Layer）

### 6.1 职责

基于本地数据库的行情数据，提供技术指标计算、策略回测、综合分析能力。

### 6.2 核心设计原则

- **100% 离线计算**：所有数据从 DuckDB 读取，不依赖网络
- **指标自动发现**：通过装饰器自动注册，无需手动维护列表
- **标准数据模型**：输入输出格式统一

### 6.3 核心模块

#### api.py —— 统一入口

```python
class QuantAPI:
    def analyze_stock(self, code: str, indicators: list[str] = None) -> dict:
        """综合分析一只股票"""
        
    def backtest(self, strategy: dict, code: str, start: str, end: str) -> dict:
        """回测策略"""
        
    def get_market_snapshot(self) -> dict:
        """市场概况"""
```

#### indicators/ —— 指标实现

```python
# indicators/ma.py
from quant.registry import register_indicator

@register_indicator("MA", category="trend")
def calculate_ma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """移动平均线"""
    return df["close"].rolling(window=window).mean()
```

#### registry.py —— 指标自动发现

启动时扫描 `quant/indicators/` 目录，收集所有 `@register_indicator` 装饰的函数，自动生成 `registry/indicators.yaml`。

### 6.4 指标注册表（自动生成）

```yaml
# registry/indicators.yaml
auto_discovered:
  MA:
    module: "quant.indicators.ma"
    func: "calculate_ma"
    category: "trend"
    params:
      window: {type: "int", default: 20, range: [5, 250]}
  
  MACD:
    module: "quant.indicators.macd"
    func: "calculate_macd"
    category: "momentum"
    params:
      fast: {type: "int", default: 12}
      slow: {type: "int", default: 26}
      signal: {type: "int", default: 9}
```

### 6.5 目录结构

```
quant/
├── __init__.py
├── registry.py
├── api.py
├── models.py
├── indicators/
│   ├── __init__.py
│   ├── ma.py
│   ├── macd.py
│   ├── rsi.py
│   └── fund_flow.py
├── backtest/
└── strategies/
```

### 6.6 扩展方式

新增指标 = 写 `indicators/xxx.py`（带 `@register_indicator`），**自动注册，零配置**。

---

## 7. 注册中心（Registry）

### 7.1 职责

Registry 是 PersonaX 的**配置驱动核心**。所有组件（角色、知识库、数据源、指标）都在 Registry 中登记，各层通过 Registry 发现和配置自己依赖的组件。

### 7.2 设计原则

- **单一可信源（Single Source of Truth）**：所有配置集中管理，避免分散在代码中
- **声明式配置**：新增组件只需声明，无需改代码
- **运行时动态发现**：启动时加载 Registry，根据当前角色确定可用资源

### 7.3 目录结构

```
registry/
├── personas.yaml
├── knowledge_bases.yaml
├── data_sources.yaml
├── indicators.yaml
└── base_templates/
    ├── investor_advisor.md
    ├── macro_analyst.md
    └── value_investor.md
```

### 7.4 配置加载流程

```
启动时：
  1. 加载 registry/*.yaml
  2. 人格层：根据 personas.yaml 确定当前角色的知识库、数据源、功能开关
  3. 知识层：根据 knowledge_bases.yaml 初始化 ChromaDB collection
  4. 数据层：根据 data_sources.yaml 初始化数据源实例（按优先级排序）
  5. 量化层：扫描 indicators/ 目录，自动生成/更新 indicators.yaml
```

---

## 8. 数据流

### 8.1 完整请求生命周期

**用户提问：** "Z哥，宁德时代现在能买吗？"

```
1. 人格层（SKILL.md）
   └── 激活 Z 哥角色
   └── 判断：涉及具体股票，需要事实支撑
   └── 读取 personas.yaml：quant_enabled=true, multi_turn_diagnosis=true

2. 知识层查询
   └── Bash: python bridge/knowledge_bridge.py --persona zettaranc "宁德时代 估值"
   └── 读取 personas.yaml：knowledge_bases=["zettaranc", "common"]
   └── 通义千问 Embedding 将问题向量化
   └── ChromaDB 查询 zettaranc + common collection
   └── 返回 top-5 知识片段（含来源引用）

3. 量化层分析
   └── Bash: python bridge/quant_bridge.py --persona zettaranc --task analyze --code 300750
   └── 读取 personas.yaml：default_indicators=["MA", "MACD", "RSI", "FUND_FLOW"]
   └── QuantAPI 调用 data.db.get_daily('300750')
   └── 从 DuckDB 读取历史行情（离线，零 API 调用）
   └── 计算 MA/MACD/RSI/资金流向
   └── 返回：技术指标状态 + 趋势判断

4. 数据层（按需补数据）
   └── 如果本地缺少 300750 最新数据
   └── SyncEngine 读取 data_sources.yaml
   └── 按优先级：Tushare → AkShare → ...
   └── 增量同步到 DuckDB
   └── 量化层重新查询

5. LLM 融合生成
   └── 人格语气（Z哥口吻）
   └── + 知识库引用（[[估值方法#PE]]、[[新能源赛道分析]]）
   └── + 量化数据（MA 金叉、MACD 红柱、主力净流入）
   └── = 完整回答
```

---

## 9. 扩展性验证

### 9.1 扩展矩阵

| 扩展场景 | 操作步骤 | 核心代码修改 |
|---------|---------|-------------|
| 新增角色 | personas.yaml + 新建 personas/<name>/ 目录 | **0 处** |
| 新增知识库 | knowledge_bases.yaml + 指定 vault 路径 | **0 处** |
| 新增数据源 | data_sources.yaml + 实现 DataSource 子类 | **0 处** |
| 新增指标 | 写 indicators/xxx.py（自动注册） | **0 处** |
| 角色切换知识库 | 改 personas.yaml 的 knowledge_bases | **0 处** |
| 数据源优先级调整 | 改 data_sources.yaml 的 priority | **0 处** |
| 指标默认参数调整 | 改 indicators.yaml | **0 处** |

### 9.2 扩展示例

#### 示例 1：新增角色"国老"

```yaml
# registry/personas.yaml
guolao:
  name: "国老"
  base_template: "value_investor"
  knowledge_bases: ["guolao", "common"]
  data_sources: ["tushare"]
  features:
    quant_enabled: true
    multi_turn_diagnosis: false
  quant_overrides:
    default_indicators: ["PE", "PB", "ROE"]
```

```
personas/guolao/
├── SKILL.md
├── personality.md
└── overrides.yaml
```

**核心代码零修改。**

#### 示例 2：新增数据源"东方财富"

```yaml
# registry/data_sources.yaml
eastmoney:
  name: "东方财富"
  type: "api"
  priority: 3
  enabled: true
  module: "data.sources.eastmoney_source"
  class: "EastMoneySource"
  config:
    base_url: "https://..."
  supported_tables:
    - daily_prices
    - fund_flow
```

```python
# data/sources/eastmoney_source.py
class EastMoneySource(DataSource):
    name = "eastmoney"
    priority = 3
    
    def get_daily(self, code, start, end):
        ...
```

**核心代码零修改。**

#### 示例 3：新增指标"布林带"

```python
# quant/indicators/boll.py
from quant.registry import register_indicator

@register_indicator("BOLL", category="trend")
def calculate_boll(df: pd.DataFrame, window: int = 20, std_dev: int = 2):
    """布林带"""
    ma = df['close'].rolling(window=window).mean()
    std = df['close'].rolling(window=window).std()
    return {
        'upper': ma + std_dev * std,
        'middle': ma,
        'lower': ma - std_dev * std
    }
```

**启动时自动注册，零手动配置。**

---

## 10. 完整目录结构

```
personax/
├── registry/                           # 注册中心（配置驱动扩展）
│   ├── personas.yaml
│   ├── knowledge_bases.yaml
│   ├── data_sources.yaml
│   ├── indicators.yaml
│   └── base_templates/
│       ├── investor_advisor.md
│       ├── macro_analyst.md
│       └── value_investor.md
│
├── personas/                           # 人格层
│   ├── zettaranc/
│   │   ├── SKILL.md
│   │   ├── personality.md
│   │   └── overrides.yaml
│   ├── qishui/
│   │   ├── SKILL.md
│   │   ├── personality.md
│   │   └── overrides.yaml
│   └── fupeng/
│       └── ...
│
├── knowledge/                          # 知识层
│   ├── __init__.py
│   ├── config.yaml
│   ├── models.py
│   ├── embeddings.py                   # 通义千问 Embedding
│   ├── chunker.py                      # Markdown 切分
│   ├── store.py                        # ChromaDB 多 collection
│   ├── query.py                        # 查询路由（按 Registry）
│   ├── sync.py                         # Obsidian 同步引擎
│   └── vector_store/                   # ChromaDB 数据（gitignore）
│       ├── zettaranc/
│       ├── qishui/
│       └── common/
│
├── data/                               # 数据层
│   ├── __init__.py
│   ├── registry.py                     # 数据源发现与管理
│   ├── db.py                           # DuckDB 封装
│   ├── schema.sql                      # 数据库 Schema
│   ├── models.py
│   ├── sync.py                         # 同步引擎（多源优先级+Fallback）
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py                     # DataSource 抽象基类
│   │   ├── tushare_source.py           # Tushare 实现
│   │   ├── akshare_source.py           # AkShare 预留
│   │   └── yahoo_source.py             # Yahoo Finance 预留
│   └── cache/
│       └── market.duckdb               # DuckDB 数据文件（gitignore）
│
├── quant/                              # 量化层
│   ├── __init__.py
│   ├── registry.py                     # 指标自动发现
│   ├── api.py                          # 统一入口（100% 离线）
│   ├── models.py
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── ma.py                       # @register_indicator("MA")
│   │   ├── macd.py                     # @register_indicator("MACD")
│   │   ├── rsi.py
│   │   └── fund_flow.py
│   ├── backtest/
│   └── strategies/
│
├── shared/                             # 共享基础设施
│   ├── __init__.py
│   ├── config.py                       # Registry 加载器
│   ├── models.py                       # 跨层共享模型
│   └── exceptions.py
│
├── bridge/                             # 桥接层（CLI 入口）
│   ├── knowledge_bridge.py             # python bridge/knowledge_bridge.py --persona zettaranc "问题"
│   └── quant_bridge.py                 # python bridge/quant_bridge.py --persona zettaranc --task analyze --code 300750
│
├── scripts/                            # 工具脚本
│   ├── sync_knowledge.py               # python scripts/sync_knowledge.py --kb zettaranc
│   ├── sync_data.py                    # python scripts/sync_data.py --code 300750
│   └── setup.py                        # 初始化（建表、配环境）
│
├── tests/
│   ├── test_persona/
│   ├── test_knowledge/
│   ├── test_data/
│   └── test_quant/
│
├── requirements.txt
├── .env.example                        # 环境变量模板
└── README.md
```

---

## 11. 技术栈汇总

| 层级 | 技术组件 | 用途 |
|------|---------|------|
| 人格层 | Markdown + YAML | 角色定义与配置 |
| 知识层 | ChromaDB | 本地向量数据库 |
| 知识层 | 通义千问 text-embedding-v3 | 中文 Embedding 模型 |
| 数据层 | DuckDB | 本地分析型数据库 |
| 数据层 | Tushare / AkShare | 金融数据 API |
| 量化层 | NumPy / Pandas | 数值计算 |
| 量化层 | 自定义装饰器 | 指标自动发现 |
| 注册中心 | YAML | 声明式配置 |
| 桥接层 | Python CLI | Claude Code 调用入口 |

---

## 12. 环境依赖

### 12.1 必需环境变量

```bash
# .env
DASHSCOPE_API_KEY=sk-xxx              # 通义千问 Embedding API Key
TUSHARE_TOKEN=xxx                     # Tushare Token
```

### 12.2 Python 依赖

```
# requirements.txt
chromadb>=0.4.0                       # 向量数据库
duckdb>=0.10.0                        # 本地分析数据库
tushare>=1.3.0                        # Tushare 数据接口
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0                           # YAML 配置解析
python-dotenv>=1.0.0                  # 环境变量加载
requests>=2.31.0                      # HTTP 请求
tqdm>=4.65.0                          # 进度条
```

---

## 13. 风险与限制

### 13.1 已知限制

1. **Claude Code 约束**：人格层必须通过 SKILL.md 静态配置，无法实现真正的"运行时动态切换人格"
2. **Embedding 成本**：通义千问 API 按 token 计费，大规模知识库同步有成本
3. **数据覆盖**：Tushare 免费版有接口频次限制，全市场历史数据同步需要时间和额度
4. **DuckDB 并发**：DuckDB 是单写入者模型，不适合多进程同时写入

### 13.2 缓解策略

1. **增量同步**：知识库和行情数据都只同步变更部分
2. **本地缓存**：Embedding 结果可缓存，避免重复计算
3. **分库策略**：如数据量过大，可按年份/市场分 DuckDB 文件
4. **队列写入**：同步任务串行化，避免并发写入冲突

---

## 14. 演进路线

### Phase 1：MVP（单角色验证）

- [ ] 实现 Z 哥角色的完整链路（人格 + 知识 + 量化）
- [ ] 知识库同步和查询
- [ ] 数据层同步和查询
- [ ] 3-5 个核心指标
- [ ] 基础回测能力

### Phase 2：多角色支持

- [ ] 引入 Registry 机制
- [ ] 支持 3-5 个角色（Z哥、啟水、傅鹏、BOSS墨、国老）
- [ ] 角色切换命令

### Phase 3：数据源扩展

- [ ] AkShare 数据源
- [ ] 港股/美股数据支持
- [ ] 实时行情 WebSocket

### Phase 4：高级功能

- [ ] 组合策略回测
- [ ] 多因子选股
- [ ] 可视化报表
- [ ] 对话历史持久化

---

## 15. 附录

### 15.1 术语表

| 术语 | 含义 |
|------|------|
| 思维蒸馏 | 从人物的言论、文章、决策中提取核心思维模型的过程 |
| 表达 DNA | 一个人独特的语言风格，包括语气、节奏、口头禅、修辞习惯 |
| Registry | 注册中心，PersonaX 的配置驱动核心 |
| Embedding | 将文本转换为高维向量，用于语义搜索 |
| Collection | ChromaDB 中的数据集合，每个知识库对应一个 collection |

### 15.2 参考资料

- [Claude Code Skill 文档](https://docs.anthropic.com/en/docs/claude-code/skills)
- [ChromaDB 官方文档](https://docs.trychroma.com/)
- [DuckDB 官方文档](https://duckdb.org/docs/)
- [Tushare 数据接口](http://tsy.xiaodefa.cn)
- [通义千问 Embedding API](https://help.aliyun.com/zh/dashscope/)

---

*文档结束*
