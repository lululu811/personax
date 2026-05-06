# PersonaX MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the PersonaX MVP — a single-role (Zettaranc) agent with working knowledge retrieval, local data cache, and quantitative analysis capabilities.

**Architecture:** Four-layer decoupled system (Persona/Knowledge/Data/Quant) with Registry-driven configuration. All data operations are offline (DuckDB), knowledge uses ChromaDB + Tongyi Embedding, quant computes indicators locally.

**Tech Stack:** Python 3.10+, ChromaDB, DuckDB, Tongyi Qianwen Embedding API, Tushare, Pandas, NumPy

---

## File Structure Overview

```
personax/
├── registry/
│   ├── personas.yaml
│   ├── knowledge_bases.yaml
│   ├── data_sources.yaml
│   └── indicators.yaml
├── personas/
│   └── zettaranc/
│       ├── SKILL.md
│       ├── personality.md
│       └── overrides.yaml
├── knowledge/
│   ├── __init__.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── store.py
│   ├── query.py
│   └── sync.py
├── data/
│   ├── __init__.py
│   ├── db.py
│   ├── schema.sql
│   ├── sync.py
│   └── sources/
│       ├── __init__.py
│       ├── base.py
│       └── tushare_source.py
├── quant/
│   ├── __init__.py
│   ├── registry.py
│   ├── api.py
│   └── indicators/
│       ├── __init__.py
│       ├── ma.py
│       ├── macd.py
│       └── rsi.py
├── shared/
│   ├── __init__.py
│   └── config.py
├── bridge/
│   ├── __init__.py
│   ├── knowledge_bridge.py
│   └── quant_bridge.py
├── scripts/
│   ├── setup.py
│   ├── sync_knowledge.py
│   └── sync_data.py
├── tests/
│   ├── __init__.py
│   ├── test_knowledge/
│   ├── test_data/
│   ├── test_quant/
│   └── test_integration.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Task 1: Project Skeleton and Infrastructure

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `shared/__init__.py`
- Create: `shared/config.py`
- Create: `registry/personas.yaml`
- Create: `registry/knowledge_bases.yaml`
- Create: `registry/data_sources.yaml`
- Create: `tests/__init__.py`

### Step 1.1: Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
chromadb>=0.4.0
duckdb>=0.10.0
tushare>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0
python-dotenv>=1.0.0
requests>=2.31.0
tqdm>=4.65.0
pytest>=7.4.0
pytest-cov>=4.1.0
EOF
```

### Step 1.2: Create .env.example

```bash
cat > .env.example << 'EOF'
# Tongyi Qianwen Embedding API (required for knowledge layer)
DASHSCOPE_API_KEY=sk-your-dashscope-api-key

# Tushare Token (required for data layer)
TUSHARE_TOKEN=your-tushare-token
EOF
```

### Step 1.3: Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Environment
.env
.venv/
venv/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Database cache
data/cache/
knowledge/vector_store/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF
```

### Step 1.4: Create shared/config.py

```bash
mkdir -p shared registry tests
```

```python
# shared/config.py
import os
import yaml
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parent.parent


def load_yaml(name: str) -> dict[str, Any]:
    path = _PROJECT_ROOT / "registry" / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_registry() -> dict[str, Any]:
    return {
        "personas": load_yaml("personas"),
        "knowledge_bases": load_yaml("knowledge_bases"),
        "data_sources": load_yaml("data_sources"),
        "indicators": load_yaml("indicators"),
    }


def get_persona_config(persona_name: str) -> dict[str, Any]:
    personas = load_yaml("personas")["personas"]
    if persona_name not in personas:
        raise ValueError(f"Unknown persona: {persona_name}")
    return personas[persona_name]


def get_knowledge_base_config(kb_name: str) -> dict[str, Any]:
    kbs = load_yaml("knowledge_bases")["knowledge_bases"]
    if kb_name not in kbs:
        raise ValueError(f"Unknown knowledge base: {kb_name}")
    return kbs[kb_name]


def get_data_source_config(ds_name: str) -> dict[str, Any]:
    sources = load_yaml("data_sources")["data_sources"]
    if ds_name not in sources:
        raise ValueError(f"Unknown data source: {ds_name}")
    return sources[ds_name]


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
```

### Step 1.5: Create registry YAML files

```yaml
# registry/personas.yaml
personas:
  zettaranc:
    name: "Z哥"
    display_name: "万千"
    base_template: "investor_advisor"
    description: "基于Z哥直播/课程提炼的投资思维模型"
    knowledge_bases:
      - zettaranc
      - common
    data_sources:
      - tushare
    features:
      quant_enabled: true
      multi_turn_diagnosis: true
      web_search: false
    quant_overrides:
      default_indicators: ["MA", "MACD", "RSI"]
      default_backtest_period: 252
```

```yaml
# registry/knowledge_bases.yaml
knowledge_bases:
  zettaranc:
    name: "Z哥投资框架"
    description: "Zettaranc直播、课程、文章整理"
    vault_path: "/home/chenlei/001_AI/knowledge_base/zettaranc-knowledge"
    collection: "zettaranc"
    embedding:
      provider: "dashscope"
      model: "text-embedding-v3"
      api_key_env: "DASHSCOPE_API_KEY"
      batch_size: 25
    chunker:
      strategy: "heading"
      max_chunk_size: 1000
      preserve_hierarchy: true
    sync:
      trigger: "manual"
      include_patterns:
        - "*.md"
      exclude_patterns:
        - "assets/**"
        - "templates/**"
        - ".obsidian/**"

  common:
    name: "通用金融知识"
    description: "通用投资术语、方法论"
    vault_path: "/home/chenlei/001_AI/knowledge_base/common-knowledge"
    collection: "common"
    embedding:
      provider: "dashscope"
      model: "text-embedding-v3"
      api_key_env: "DASHSCOPE_API_KEY"
      batch_size: 25
    chunker:
      strategy: "paragraph"
      max_chunk_size: 800
    sync:
      trigger: "manual"
```

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
      rate_limit: 200
    supported_tables:
      - daily_prices
      - fund_flow
      - financials
      - stocks
      - index_prices
    fallback: []
```

```yaml
# registry/indicators.yaml
# Auto-generated by quant/registry.py on startup
auto_discovered: {}

custom: {}
```

### Step 1.6: Create empty __init__.py files

```bash
touch shared/__init__.py tests/__init__.py
```

### Step 1.7: Write test for config loader

```python
# tests/test_shared/test_config.py
import pytest
from shared.config import get_persona_config, get_knowledge_base_config


def test_get_persona_config():
    cfg = get_persona_config("zettaranc")
    assert cfg["name"] == "Z哥"
    assert "tushare" in cfg["data_sources"]
    assert cfg["features"]["quant_enabled"] is True


def test_get_knowledge_base_config():
    cfg = get_knowledge_base_config("zettaranc")
    assert cfg["collection"] == "zettaranc"
    assert cfg["chunker"]["strategy"] == "heading"
```

### Step 1.8: Run tests

```bash
cd /home/chenlei/001_AI/personax
python -m pytest tests/test_shared/test_config.py -v
```

**Expected:** Both tests PASS.

### Step 1.9: Commit

```bash
git add requirements.txt .env.example .gitignore shared/ registry/ tests/
git commit -m "feat: project skeleton and registry configuration"
```

---

## Task 2: Data Layer — Database and Schema

**Files:**
- Create: `data/__init__.py`
- Create: `data/schema.sql`
- Create: `data/db.py`
- Create: `tests/test_data/__init__.py`
- Create: `tests/test_data/test_db.py`

### Step 2.1: Create data/schema.sql

```sql
-- stocks: basic stock information
CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    industry VARCHAR(50),
    market VARCHAR(10),
    list_date DATE,
    is_active BOOLEAN DEFAULT true
);

-- daily_prices: daily OHLCV data (core table)
CREATE TABLE IF NOT EXISTS daily_prices (
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
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (code, trade_date)
);

-- fund_flow: capital flow data
CREATE TABLE IF NOT EXISTS fund_flow (
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

-- financials: financial report data
CREATE TABLE IF NOT EXISTS financials (
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

-- sync_log: data synchronization log
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR(50),
    code VARCHAR(20),
    data_source VARCHAR(20),
    start_date DATE,
    end_date DATE,
    records_count INTEGER,
    status VARCHAR(20),
    error_msg VARCHAR(500),
    synced_at TIMESTAMP DEFAULT now()
);
```

### Step 2.2: Create data/db.py

```python
# data/db.py
from pathlib import Path
import duckdb
import pandas as pd

_DB_PATH = Path(__file__).parent / "cache" / "market.duckdb"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(_DB_PATH)
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._init_tables()

    def _init_tables(self):
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.execute(f.read())

    # ------------------ Query APIs ------------------

    def get_daily(self, code: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        sql = """
            SELECT * FROM daily_prices
            WHERE code = ?
            {start_filter}
            {end_filter}
            ORDER BY trade_date
        """.format(
            start_filter="AND trade_date >= ?" if start else "",
            end_filter="AND trade_date <= ?" if end else "",
        )
        params = [code]
        if start:
            params.append(start)
        if end:
            params.append(end)
        return self.conn.execute(sql, params).df()

    def get_fund_flow(self, code: str, days: int = 30) -> pd.DataFrame:
        sql = """
            SELECT * FROM fund_flow
            WHERE code = ?
              AND trade_date >= (SELECT MAX(trade_date) FROM fund_flow WHERE code = ?) - INTERVAL '%s days'
            ORDER BY trade_date
        """ % days
        return self.conn.execute(sql, [code, code]).df()

    def get_financials(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM financials
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_last_trade_date(self, code: str, table: str = "daily_prices") -> str | None:
        sql = f"""
            SELECT MAX(trade_date) as max_date FROM {table}
            WHERE code = ?
        """
        result = self.conn.execute(sql, [code]).fetchone()
        return result[0].strftime("%Y%m%d") if result and result[0] else None

    def check_data_gaps(self, code: str, table: str = "daily_prices") -> list[tuple[str, str]]:
        sql = f"""
            WITH dates AS (
                SELECT trade_date,
                       LAG(trade_date) OVER (ORDER BY trade_date) as prev_date
                FROM {table}
                WHERE code = ?
            )
            SELECT prev_date, trade_date
            FROM dates
            WHERE prev_date IS NOT NULL
              AND trade_date - prev_date > 1
            ORDER BY prev_date
        """
        return self.conn.execute(sql, [code]).fetchall()

    # ------------------ Insert APIs ------------------

    def insert(self, table: str, df: pd.DataFrame):
        if df.empty:
            return
        self.conn.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM df", {"df": df})

    def log_sync(self, table_name: str, code: str | None, data_source: str,
                 start_date: str, end_date: str, records_count: int,
                 status: str = "success", error_msg: str = ""):
        self.conn.execute("""
            INSERT INTO sync_log (table_name, code, data_source, start_date, end_date, records_count, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [table_name, code, data_source, start_date, end_date, records_count, status, error_msg])

    def close(self):
        self.conn.close()
```

### Step 2.3: Write test for Database

```python
# tests/test_data/test_db.py
import pytest
import pandas as pd
from data.db import Database


@pytest.fixture
def db():
    db = Database(":memory:")
    yield db
    db.close()


def test_init_tables(db):
    tables = db.conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    assert "daily_prices" in table_names
    assert "fund_flow" in table_names
    assert "financials" in table_names
    assert "sync_log" in table_names


def test_insert_and_get_daily(db):
    df = pd.DataFrame({
        "code": ["000001.SZ"],
        "trade_date": [pd.Timestamp("2024-01-01")],
        "open": [10.0],
        "high": [11.0],
        "low": [9.5],
        "close": [10.5],
        "volume": [1000000],
        "amount": [10000000.0],
        "change_pct": [0.05],
        "turnover_rate": [0.02],
        "source": ["test"],
    })
    db.insert("daily_prices", df)

    result = db.get_daily("000001.SZ")
    assert len(result) == 1
    assert result.iloc[0]["close"] == 10.5


def test_get_last_trade_date(db):
    df = pd.DataFrame({
        "code": ["000001.SZ", "000001.SZ"],
        "trade_date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
        "open": [10.0, 10.5],
        "high": [11.0, 11.5],
        "low": [9.5, 10.0],
        "close": [10.5, 11.0],
        "volume": [1000000, 2000000],
        "amount": [10000000.0, 20000000.0],
        "change_pct": [0.05, 0.0476],
        "turnover_rate": [0.02, 0.04],
        "source": ["test", "test"],
    })
    db.insert("daily_prices", df)

    last_date = db.get_last_trade_date("000001.SZ")
    assert last_date == "20240102"
```

### Step 2.4: Run tests

```bash
python -m pytest tests/test_data/test_db.py -v
```

**Expected:** All tests PASS.

### Step 2.5: Commit

```bash
git add data/ tests/test_data/
git commit -m "feat: data layer - DuckDB schema and database class"
```

---

## Task 3: Data Layer — Tushare Data Source

**Files:**
- Create: `data/sources/__init__.py`
- Create: `data/sources/base.py`
- Create: `data/sources/tushare_source.py`
- Create: `tests/test_data/test_tushare_source.py`

### Step 3.1: Create data/sources/base.py

```python
# data/sources/base.py
from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    name: str = ""
    priority: int = 999

    @abstractmethod
    def get_daily(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return standardized DataFrame with columns:
        code, trade_date, open, high, low, close, volume, amount, change_pct, turnover_rate, source
        """
        ...

    @abstractmethod
    def get_fund_flow(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return standardized DataFrame with columns:
        code, trade_date, main_in, main_out, main_net, retail_in, retail_out, retail_net, total_amount, source
        """
        ...

    @abstractmethod
    def get_stocks(self) -> pd.DataFrame:
        """Return all stock basic info."""
        ...
```

### Step 3.2: Create data/sources/tushare_source.py

```python
# data/sources/tushare_source.py
import os
from pathlib import Path

import pandas as pd
import tushare as ts

from data.sources.base import DataSource

_DAILY_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "vol": "volume",
    "amount": "amount",
    "pct_chg": "change_pct",
    "turnover_rate": "turnover_rate",
}

_FUND_FLOW_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "main_buy": "main_in",
    "main_sell": "main_out",
    "main_net_amount": "main_net",
    "retail_buy": "retail_in",
    "retail_sell": "retail_out",
    "retail_net_amount": "retail_net",
    "total_amount": "total_amount",
}


class TushareSource(DataSource):
    name = "tushare"
    priority = 1

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        token = os.environ.get(cfg.get("token_env", "TUSHARE_TOKEN"))
        if not token:
            raise ValueError("TUSHARE_TOKEN not set in environment")

        ts.set_token(token)
        self.pro = ts.pro_api()
        url = cfg.get("base_url", "http://tsy.xiaodefa.cn")
        self.pro._DataApi__http_url = url

    def _standardize(self, df: pd.DataFrame, col_map: dict, source: str) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.rename(columns=col_map)
        df["source"] = source
        # Ensure all expected columns exist
        for col in col_map.values():
            if col not in df.columns:
                df[col] = None
        return df[list(col_map.values()) + ["source"]]

    def get_daily(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.daily(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _DAILY_COLS, "tushare")

    def get_fund_flow(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.moneyflow(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _FUND_FLOW_COLS, "tushare")

    def get_stocks(self) -> pd.DataFrame:
        df = self.pro.stock_basic(exchange="", list_status="L")
        df = df.rename(columns={
            "ts_code": "code",
            "name": "name",
            "industry": "industry",
            "market": "market",
            "list_date": "list_date",
        })
        df["is_active"] = True
        df["source"] = "tushare"
        return df[["code", "name", "industry", "market", "list_date", "is_active", "source"]]
```

### Step 3.3: Write test (mock-based)

```python
# tests/test_data/test_tushare_source.py
import pytest
from unittest.mock import Mock, patch
from data.sources.tushare_source import TushareSource


@pytest.fixture
def source():
    with patch.dict("os.environ", {"TUSHARE_TOKEN": "fake_token"}):
        with patch("data.sources.tushare_source.ts") as mock_ts:
            mock_pro = Mock()
            mock_ts.pro_api.return_value = mock_pro
            src = TushareSource()
            src.pro = mock_pro
            return src


def test_get_daily(source):
    import pandas as pd
    source.pro.daily.return_value = pd.DataFrame({
        "ts_code": ["000001.SZ"],
        "trade_date": ["20240101"],
        "open": [10.0],
        "high": [11.0],
        "low": [9.0],
        "close": [10.5],
        "vol": [1000000],
        "amount": [10000000.0],
        "pct_chg": [5.0],
        "turnover_rate": [2.0],
    })

    df = source.get_daily("000001.SZ", "20240101", "20240101")
    assert len(df) == 1
    assert df.iloc[0]["code"] == "000001.SZ"
    assert df.iloc[0]["close"] == 10.5
    assert df.iloc[0]["source"] == "tushare"
```

### Step 3.4: Run tests

```bash
python -m pytest tests/test_data/test_tushare_source.py -v
```

**Expected:** Test PASS.

### Step 3.5: Commit

```bash
git add data/sources/ tests/test_data/test_tushare_source.py
git commit -m "feat: data layer - Tushare data source implementation"
```

---

## Task 4: Data Layer — Sync Engine

**Files:**
- Create: `data/sync.py`
- Create: `tests/test_data/test_sync.py`

### Step 4.1: Create data/sync.py

```python
# data/sync.py
import importlib
from datetime import datetime, timedelta
from typing import Type

from data.db import Database
from data.sources.base import DataSource
from shared.config import load_yaml


class SyncEngine:
    def __init__(self, persona_name: str | None = None):
        self.db = Database()
        self.sources = self._load_sources(persona_name)

    def _load_sources(self, persona_name: str | None = None) -> list[DataSource]:
        registry = load_yaml("data_sources")["data_sources"]
        sources = []

        for name, cfg in registry.items():
            if not cfg.get("enabled", False):
                continue
            if persona_name:
                from shared.config import get_persona_config
                allowed = get_persona_config(persona_name)["data_sources"]
                if name not in allowed:
                    continue

            module_path = cfg["module"]
            class_name = cfg["class"]
            mod = importlib.import_module(module_path)
            cls: Type[DataSource] = getattr(mod, class_name)
            instance = cls(cfg.get("config", {}))
            sources.append(instance)

        return sorted(sources, key=lambda s: s.priority)

    def sync_stock_daily(self, code: str):
        last_date = self.db.get_last_trade_date(code, "daily_prices")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20180101"
        end = datetime.now().strftime("%Y%m%d")

        if start > end:
            return 0

        for source in self.sources:
            try:
                df = source.get_daily(code, start, end)
                if not df.empty:
                    self.db.insert("daily_prices", df)
                    self.db.log_sync("daily_prices", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} daily: {e}")
                continue
        return 0

    def sync_stock_fund_flow(self, code: str):
        last_date = self.db.get_last_trade_date(code, "fund_flow")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20240101"
        end = datetime.now().strftime("%Y%m%d")

        if start > end:
            return 0

        for source in self.sources:
            try:
                df = source.get_fund_flow(code, start, end)
                if not df.empty:
                    self.db.insert("fund_flow", df)
                    self.db.log_sync("fund_flow", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} fund_flow: {e}")
                continue
        return 0

    def sync_stock(self, code: str):
        daily_count = self.sync_stock_daily(code)
        flow_count = self.sync_stock_fund_flow(code)
        return {"daily_prices": daily_count, "fund_flow": flow_count}

    def sync_stocks_list(self):
        for source in self.sources:
            try:
                df = source.get_stocks()
                if not df.empty:
                    self.db.insert("stocks", df)
                    self.db.log_sync("stocks", None, source.name, "", "", len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for stocks list: {e}")
                continue
        return 0
```

### Step 4.2: Write test

```python
# tests/test_data/test_sync.py
import pytest
from unittest.mock import Mock, patch
from data.sync import SyncEngine


@pytest.fixture
def engine():
    with patch("data.sync.Database") as MockDB:
        db = Mock()
        MockDB.return_value = db
        db.get_last_trade_date.return_value = None

        with patch("data.sync.load_yaml") as mock_yaml:
            mock_yaml.return_value = {
                "data_sources": {
                    "tushare": {
                        "enabled": True,
                        "module": "data.sources.tushare_source",
                        "class": "TushareSource",
                        "config": {},
                    }
                }
            }

            with patch("data.sync.importlib.import_module"):
                eng = SyncEngine()
                eng.sources = [Mock()]
                eng.sources[0].name = "tushare"
                eng.sources[0].priority = 1
                eng.db = db
                return eng


def test_sync_stock_daily(engine):
    import pandas as pd
    engine.sources[0].get_daily.return_value = pd.DataFrame({
        "code": ["000001.SZ"],
        "trade_date": [pd.Timestamp("2024-01-01")],
        "open": [10.0],
        "high": [11.0],
        "low": [9.0],
        "close": [10.5],
        "volume": [1000000],
        "amount": [10000000.0],
        "change_pct": [5.0],
        "turnover_rate": [2.0],
        "source": ["tushare"],
    })

    result = engine.sync_stock_daily("000001.SZ")
    assert result == 1
    engine.db.insert.assert_called_once()
```

### Step 4.3: Run tests

```bash
python -m pytest tests/test_data/test_sync.py -v
```

**Expected:** Test PASS.

### Step 4.4: Commit

```bash
git add data/sync.py tests/test_data/test_sync.py
git commit -m "feat: data layer - sync engine with multi-source fallback"
```

---

## Task 5: Knowledge Layer — Markdown Chunker

**Files:**
- Create: `knowledge/__init__.py`
- Create: `knowledge/chunker.py`
- Create: `tests/test_knowledge/__init__.py`
- Create: `tests/test_knowledge/test_chunker.py`

### Step 5.1: Create knowledge/chunker.py

```python
# knowledge/chunker.py
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    content: str
    source_file: str
    heading_path: str
    start_line: int
    end_line: int


class MarkdownChunker:
    def __init__(self, max_size: int = 1000, preserve_hierarchy: bool = True):
        self.max_size = max_size
        self.preserve_hierarchy = preserve_hierarchy

    def split_file(self, file_path: Path) -> list[Chunk]:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        return self.split_text(content, str(file_path))

    def split_text(self, text: str, source_file: str = "") -> list[Chunk]:
        lines = text.split("\n")
        chunks = []
        current_heading_path = ""
        current_lines = []
        current_start = 0

        for i, line in enumerate(lines):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous chunk
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(Chunk(
                            content=chunk_text,
                            source_file=source_file,
                            heading_path=current_heading_path,
                            start_line=current_start,
                            end_line=i - 1,
                        ))

                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Update heading path
                if self.preserve_hierarchy:
                    parts = current_heading_path.split(" > ") if current_heading_path else []
                    parts = parts[:level - 1] + [title]
                    current_heading_path = " > ".join(parts)
                else:
                    current_heading_path = title

                current_lines = [line]
                current_start = i
            else:
                current_lines.append(line)

        # Save final chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(Chunk(
                    content=chunk_text,
                    source_file=source_file,
                    heading_path=current_heading_path,
                    start_line=current_start,
                    end_line=len(lines) - 1,
                ))

        # Split oversized chunks
        return self._split_oversized(chunks)

    def _split_oversized(self, chunks: list[Chunk]) -> list[Chunk]:
        result = []
        for chunk in chunks:
            if len(chunk.content) <= self.max_size:
                result.append(chunk)
                continue

            # Split by paragraphs
            paragraphs = chunk.content.split("\n\n")
            current = ""
            current_start = chunk.start_line

            for para in paragraphs:
                if len(current) + len(para) + 2 > self.max_size and current:
                    result.append(Chunk(
                        content=current.strip(),
                        source_file=chunk.source_file,
                        heading_path=chunk.heading_path,
                        start_line=current_start,
                        end_line=chunk.end_line,
                    ))
                    current = para
                else:
                    current = (current + "\n\n" + para).strip() if current else para

            if current:
                result.append(Chunk(
                    content=current.strip(),
                    source_file=chunk.source_file,
                    heading_path=chunk.heading_path,
                    start_line=current_start,
                    end_line=chunk.end_line,
                ))
        return result
```

### Step 5.2: Write test

```python
# tests/test_knowledge/test_chunker.py
from knowledge.chunker import MarkdownChunker


def test_split_by_headings():
    text = """# Title

Intro paragraph.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
    chunker = MarkdownChunker()
    chunks = chunker.split_text(text, "test.md")

    assert len(chunks) >= 2
    assert chunks[0].heading_path == "Title"
    assert "Intro paragraph" in chunks[0].content
    assert chunks[1].heading_path == "Title > Section 1"
    assert "Content of section 1" in chunks[1].content


def test_preserve_hierarchy():
    text = """# A
## B
### C
Content.
"""
    chunker = MarkdownChunker()
    chunks = chunker.split_text(text)

    paths = [c.heading_path for c in chunks]
    assert any("A > B > C" in p for p in paths)


def test_split_oversized():
    text = "# Title\n\n" + "word " * 600
    chunker = MarkdownChunker(max_size=500)
    chunks = chunker.split_text(text)

    for chunk in chunks:
        assert len(chunk.content) <= 500
```

### Step 5.3: Run tests

```bash
python -m pytest tests/test_knowledge/test_chunker.py -v
```

**Expected:** All tests PASS.

### Step 5.4: Commit

```bash
git add knowledge/ tests/test_knowledge/
git commit -m "feat: knowledge layer - markdown chunker with heading-aware splitting"
```

---

## Task 6: Knowledge Layer — Tongyi Embedding

**Files:**
- Create: `knowledge/embeddings.py`
- Create: `tests/test_knowledge/test_embeddings.py`

### Step 6.1: Create knowledge/embeddings.py

```python
# knowledge/embeddings.py
import os
import time
from typing import List

import requests


class TongyiEmbedding:
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-v3"):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings = []
        batch_size = 25

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {
                "model": self.model,
                "input": {
                    "texts": batch,
                },
            }

            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            embeddings = data["output"]["embeddings"]
            all_embeddings.extend([e["embedding"] for e in embeddings])

            time.sleep(0.1)  # Rate limit protection

        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        results = self.embed([text])
        return results[0] if results else []
```

### Step 6.2: Write test (mock-based)

```python
# tests/test_knowledge/test_embeddings.py
import pytest
from unittest.mock import Mock, patch
from knowledge.embeddings import TongyiEmbedding


@patch.dict("os.environ", {"DASHSCOPE_API_KEY": "fake_key"})
def test_embed_single():
    embedder = TongyiEmbedding()

    with patch("knowledge.embeddings.requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "output": {
                    "embeddings": [
                        {"embedding": [0.1, 0.2, 0.3]}
                    ]
                }
            },
            raise_for_status=lambda: None,
        )

        result = embedder.embed_single("test text")
        assert result == [0.1, 0.2, 0.3]


@patch.dict("os.environ", {"DASHSCOPE_API_KEY": "fake_key"})
def test_embed_batch():
    embedder = TongyiEmbedding()

    with patch("knowledge.embeddings.requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "output": {
                    "embeddings": [
                        {"embedding": [0.1, 0.2]},
                        {"embedding": [0.3, 0.4]},
                    ]
                }
            },
            raise_for_status=lambda: None,
        )

        results = embedder.embed(["text1", "text2"])
        assert len(results) == 2
        assert results[0] == [0.1, 0.2]
```

### Step 6.3: Run tests

```bash
python -m pytest tests/test_knowledge/test_embeddings.py -v
```

**Expected:** All tests PASS.

### Step 6.4: Commit

```bash
git add knowledge/embeddings.py tests/test_knowledge/test_embeddings.py
git commit -m "feat: knowledge layer - Tongyi Qianwen embedding client"
```

---

## Task 7: Knowledge Layer — Vector Store and Query

**Files:**
- Create: `knowledge/store.py`
- Create: `knowledge/query.py`
- Create: `tests/test_knowledge/test_store.py`
- Create: `tests/test_knowledge/test_query.py`

### Step 7.1: Create knowledge/store.py

```python
# knowledge/store.py
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.api.types import Include

from knowledge.embeddings import TongyiEmbedding

_DB_ROOT = Path(__file__).parent / "vector_store"


class KnowledgeStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(_DB_ROOT)
        _DB_ROOT.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.embedder = TongyiEmbedding()

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, collection_name: str, chunks: List[Any], ids: List[str] | None = None):
        collection = self.get_or_create_collection(collection_name)

        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        if ids is None:
            ids = [f"{collection_name}_{i}" for i in range(len(chunks))]

        metadatas = [
            {
                "source_file": chunk.source_file,
                "heading_path": chunk.heading_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            }
            for chunk in chunks
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(self, collection_name: str, question: str, n_results: int = 5) -> Dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        embedding = self.embedder.embed_single(question)

        return collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def delete_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]
```

### Step 7.2: Create knowledge/query.py

```python
# knowledge/query.py
from typing import List, Dict, Any

from knowledge.store import KnowledgeStore
from shared.config import get_persona_config


def query_knowledge(question: str, persona_name: str, n_results: int = 5) -> Dict[str, Any]:
    """
    Query knowledge bases for a given persona.
    Returns merged results from all allowed knowledge bases.
    """
    config = get_persona_config(persona_name)
    allowed_kb = config["knowledge_bases"]

    store = KnowledgeStore()
    all_results = {}

    for kb_name in allowed_kb:
        try:
            results = store.query(kb_name, question, n_results=n_results)
            all_results[kb_name] = results
        except Exception as e:
            all_results[kb_name] = {"error": str(e)}

    return all_results


def format_results(results: Dict[str, Any]) -> str:
    """Format query results into a context string for LLM."""
    lines = []
    for kb_name, kb_results in results.items():
        if "error" in kb_results:
            continue

        documents = kb_results.get("documents", [[]])[0]
        metadatas = kb_results.get("metadatas", [[]])[0]
        distances = kb_results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            source = meta.get("source_file", "unknown")
            heading = meta.get("heading_path", "")
            lines.append(f"[{source} > {heading}] (relevance: {1 - dist:.2f})")
            lines.append(doc[:500])  # Truncate long docs
            lines.append("---")

    return "\n".join(lines)
```

### Step 7.3: Write tests

```python
# tests/test_knowledge/test_store.py
import pytest
from unittest.mock import Mock, patch
from knowledge.store import KnowledgeStore


@patch("knowledge.store.TongyiEmbedding")
def test_add_and_query(MockEmbedder):
    mock_embedder = Mock()
    mock_embedder.embed.return_value = [[0.1, 0.2, 0.3]]
    mock_embedder.embed_single.return_value = [0.1, 0.2, 0.3]
    MockEmbedder.return_value = mock_embedder

    store = KnowledgeStore(db_path=":memory:")

    chunk = Mock()
    chunk.content = "test content"
    chunk.source_file = "test.md"
    chunk.heading_path = "Title"
    chunk.start_line = 0
    chunk.end_line = 1

    store.add_documents("test_collection", [chunk])

    # Mock query response
    mock_collection = Mock()
    mock_collection.query.return_value = {
        "documents": [["test content"]],
        "metadatas": [[{"source_file": "test.md", "heading_path": "Title"}]],
        "distances": [[0.1]],
    }
    store.client.get_or_create_collection = Mock(return_value=mock_collection)

    results = store.query("test_collection", "test question")
    assert "documents" in results
```

```python
# tests/test_knowledge/test_query.py
import pytest
from unittest.mock import Mock, patch
from knowledge.query import query_knowledge, format_results


@patch("knowledge.query.KnowledgeStore")
@patch("knowledge.query.get_persona_config")
def test_query_knowledge(mock_config, MockStore):
    mock_config.return_value = {"knowledge_bases": ["zettaranc"]}

    mock_store = Mock()
    mock_store.query.return_value = {
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"source_file": "a.md", "heading_path": "H1"}, {"source_file": "b.md", "heading_path": "H2"}]],
        "distances": [[0.1, 0.2]],
    }
    MockStore.return_value = mock_store

    results = query_knowledge("test", "zettaranc")
    assert "zettaranc" in results


def test_format_results():
    results = {
        "zettaranc": {
            "documents": [["content1", "content2"]],
            "metadatas": [[{"source_file": "a.md", "heading_path": "H1"}, {"source_file": "b.md", "heading_path": "H2"}]],
            "distances": [[0.1, 0.3]],
        }
    }
    formatted = format_results(results)
    assert "a.md > H1" in formatted
    assert "content1" in formatted
```

### Step 7.4: Run tests

```bash
python -m pytest tests/test_knowledge/test_store.py tests/test_knowledge/test_query.py -v
```

**Expected:** All tests PASS.

### Step 7.5: Commit

```bash
git add knowledge/store.py knowledge/query.py tests/test_knowledge/test_store.py tests/test_knowledge/test_query.py
git commit -m "feat: knowledge layer - vector store and query router"
```

---

## Task 8: Knowledge Layer — Sync Engine

**Files:**
- Create: `knowledge/sync.py`
- Create: `tests/test_knowledge/test_sync.py`

### Step 8.1: Create knowledge/sync.py

```python
# knowledge/sync.py
import hashlib
import json
from pathlib import Path
from typing import List

from knowledge.chunker import MarkdownChunker
from knowledge.store import KnowledgeStore
from shared.config import get_knowledge_base_config

_STATE_FILE = Path(__file__).parent / ".sync_state.json"


class KnowledgeSyncEngine:
    def __init__(self):
        self.store = KnowledgeStore()
        self.chunker = MarkdownChunker()
        self._load_state()

    def _load_state(self):
        if _STATE_FILE.exists():
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        else:
            self.state = {}

    def _save_state(self):
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _collect_md_files(self, vault_path: Path, include: List[str], exclude: List[str]) -> List[Path]:
        files = []
        for pattern in include:
            files.extend(vault_path.rglob(pattern))

        # Apply exclusions
        filtered = []
        for f in files:
            rel = f.relative_to(vault_path)
            excluded = False
            for ex in exclude:
                if rel.match(ex):
                    excluded = True
                    break
            if not excluded:
                filtered.append(f)

        return sorted(filtered)

    def sync_knowledge_base(self, kb_name: str):
        cfg = get_knowledge_base_config(kb_name)
        vault_path = Path(cfg["vault_path"])
        collection = cfg["collection"]
        chunker_cfg = cfg.get("chunker", {})
        sync_cfg = cfg.get("sync", {})

        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")

        # Update chunker config
        self.chunker.max_size = chunker_cfg.get("max_chunk_size", 1000)
        self.chunker.preserve_hierarchy = chunker_cfg.get("preserve_hierarchy", True)

        # Collect files
        include = sync_cfg.get("include_patterns", ["*.md"])
        exclude = sync_cfg.get("exclude_patterns", [".obsidian/**", "assets/**"])
        files = self._collect_md_files(vault_path, include, exclude)

        # Track changes
        kb_state = self.state.get(kb_name, {})
        changed_files = []

        for file in files:
            rel_path = str(file.relative_to(vault_path))
            current_hash = self._file_hash(file)

            if kb_state.get(rel_path) != current_hash:
                changed_files.append((file, rel_path))
                kb_state[rel_path] = current_hash

        # Remove deleted files from state
        current_paths = {str(f.relative_to(vault_path)) for f in files}
        deleted = set(kb_state.keys()) - current_paths
        for d in deleted:
            del kb_state[d]

        if not changed_files:
            print(f"Knowledge base '{kb_name}' is up to date.")
            return 0

        # Process changed files
        all_chunks = []
        for file, rel_path in changed_files:
            chunks = self.chunker.split_file(file)
            for chunk in chunks:
                chunk.source_file = rel_path
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # Delete old collection and re-add
        self.store.delete_collection(collection)
        ids = [f"{kb_name}_{i}" for i in range(len(all_chunks))]
        self.store.add_documents(collection, all_chunks, ids=ids)

        # Save state
        self.state[kb_name] = kb_state
        self._save_state()

        print(f"Synced {len(changed_files)} files, {len(all_chunks)} chunks to '{kb_name}'")
        return len(all_chunks)
```

### Step 8.2: Write test

```python
# tests/test_knowledge/test_sync.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from knowledge.sync import KnowledgeSyncEngine


@patch("knowledge.sync.KnowledgeStore")
@patch("knowledge.sync.MarkdownChunker")
@patch("knowledge.sync.get_knowledge_base_config")
def test_sync_knowledge_base(mock_config, MockChunker, MockStore):
    mock_config.return_value = {
        "vault_path": "/tmp/test_vault",
        "collection": "test_kb",
        "chunker": {"max_chunk_size": 1000, "preserve_hierarchy": True},
        "sync": {"include_patterns": ["*.md"], "exclude_patterns": []},
    }

    mock_chunker = Mock()
    mock_chunker.split_file.return_value = [
        Mock(content="chunk1", source_file="", heading_path="H1", start_line=0, end_line=1),
    ]
    MockChunker.return_value = mock_chunker

    mock_store = Mock()
    MockStore.return_value = mock_store

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob", return_value=[Path("/tmp/test_vault/test.md")]):
            with patch("knowledge.sync.KnowledgeSyncEngine._file_hash", return_value="abc123"):
                engine = KnowledgeSyncEngine()
                engine.state = {}
                count = engine.sync_knowledge_base("test_kb")
                assert count >= 0
```

### Step 8.3: Run tests

```bash
python -m pytest tests/test_knowledge/test_sync.py -v
```

**Expected:** Test PASS.

### Step 8.4: Commit

```bash
git add knowledge/sync.py tests/test_knowledge/test_sync.py
git commit -m "feat: knowledge layer - incremental sync engine with hash tracking"
```

---

## Task 9: Quant Layer — Indicator Registry

**Files:**
- Create: `quant/__init__.py`
- Create: `quant/registry.py`
- Create: `quant/indicators/__init__.py`
- Create: `quant/indicators/ma.py`
- Create: `quant/indicators/macd.py`
- Create: `quant/indicators/rsi.py`
- Create: `tests/test_quant/__init__.py`
- Create: `tests/test_quant/test_registry.py`
- Create: `tests/test_quant/test_indicators.py`

### Step 9.1: Create quant/registry.py

```python
# quant/registry.py
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Callable, Dict, Any

_INDICATORS: Dict[str, Dict[str, Any]] = {}


def register_indicator(name: str, category: str = "other"):
    def decorator(func: Callable) -> Callable:
        _INDICATORS[name] = {
            "func": func,
            "category": category,
            "module": func.__module__,
            "doc": func.__doc__ or "",
            "params": _extract_params(func),
        }
        return func
    return decorator


def _extract_params(func: Callable) -> Dict[str, Any]:
    sig = inspect.signature(func)
    params = {}
    for param_name, param in sig.parameters.items():
        if param_name == "df":
            continue
        params[param_name] = {
            "default": param.default if param.default is not inspect.Parameter.empty else None,
            "type": "float" if param.annotation == float else "int" if param.annotation == int else "any",
        }
    return params


def get_indicator(name: str) -> Callable:
    if name not in _INDICATORS:
        raise ValueError(f"Unknown indicator: {name}. Available: {list(_INDICATORS.keys())}")
    return _INDICATORS[name]["func"]


def list_indicators(category: str | None = None) -> Dict[str, Dict[str, Any]]:
    if category is None:
        return dict(_INDICATORS)
    return {k: v for k, v in _INDICATORS.items() if v["category"] == category}


def discover_indicators():
    """Auto-discover all indicators in quant/indicators/ package."""
    from quant import indicators
    pkg_path = Path(indicators.__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_"):
            continue
        importlib.import_module(f"quant.indicators.{module_name}")


def save_registry(path: Path | None = None):
    import yaml
    path = path or Path(__file__).parent.parent / "registry" / "indicators.yaml"

    data = {
        "auto_discovered": {
            name: {
                "module": info["module"],
                "category": info["category"],
                "params": info["params"],
            }
            for name, info in _INDICATORS.items()
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
```

### Step 9.2: Create indicator implementations

```python
# quant/indicators/ma.py
import pandas as pd
from quant.registry import register_indicator


@register_indicator("MA", category="trend")
def calculate_ma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Moving Average"""
    return df["close"].rolling(window=window).mean()
```

```python
# quant/indicators/macd.py
import pandas as pd
from quant.registry import register_indicator


@register_indicator("MACD", category="momentum")
def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD Indicator"""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = (dif - dea) * 2
    return {"DIF": dif, "DEA": dea, "MACD": macd}
```

```python
# quant/indicators/rsi.py
import pandas as pd
from quant.registry import register_indicator


@register_indicator("RSI", category="momentum")
def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

### Step 9.3: Write tests

```python
# tests/test_quant/test_registry.py
from quant.registry import register_indicator, get_indicator, list_indicators, discover_indicators
import pandas as pd


def test_register_and_get():
    @register_indicator("TEST_MA")
    def test_ma(df, window=20):
        return df["close"].rolling(window=window).mean()

    func = get_indicator("TEST_MA")
    assert func is not None


def test_list_indicators():
    indicators = list_indicators()
    assert "MA" in indicators
    assert "MACD" in indicators
    assert "RSI" in indicators


def test_discover():
    discover_indicators()
    indicators = list_indicators()
    assert len(indicators) >= 3
```

```python
# tests/test_quant/test_indicators.py
import pandas as pd
import numpy as np
from quant.indicators.ma import calculate_ma
from quant.indicators.macd import calculate_macd
from quant.indicators.rsi import calculate_rsi


def _make_df():
    np.random.seed(42)
    return pd.DataFrame({
        "close": 100 + np.cumsum(np.random.randn(100)),
    })


def test_ma():
    df = _make_df()
    ma = calculate_ma(df, window=20)
    assert len(ma) == len(df)
    assert pd.isna(ma.iloc[0])
    assert not pd.isna(ma.iloc[19])


def test_macd():
    df = _make_df()
    result = calculate_macd(df)
    assert "DIF" in result
    assert "DEA" in result
    assert "MACD" in result
    assert len(result["DIF"]) == len(df)


def test_rsi():
    df = _make_df()
    rsi = calculate_rsi(df, window=14)
    assert len(rsi) == len(df)
    assert pd.isna(rsi.iloc[0])
    assert not pd.isna(rsi.iloc[13])
    assert 0 <= rsi.iloc[-1] <= 100
```

### Step 9.4: Run tests

```bash
python -m pytest tests/test_quant/test_registry.py tests/test_quant/test_indicators.py -v
```

**Expected:** All tests PASS.

### Step 9.5: Commit

```bash
git add quant/ tests/test_quant/
git commit -m "feat: quant layer - indicator registry and core indicators (MA/MACD/RSI)"
```

---

## Task 10: Quant Layer — API

**Files:**
- Create: `quant/api.py`
- Create: `tests/test_quant/test_api.py`

### Step 10.1: Create quant/api.py

```python
# quant/api.py
from typing import List, Dict, Any

import pandas as pd

from data.db import Database
from quant.registry import get_indicator, list_indicators, discover_indicators
from shared.config import get_persona_config


class QuantAPI:
    def __init__(self, persona_name: str | None = None):
        self.db = Database()
        self.persona_name = persona_name
        discover_indicators()

        if persona_name:
            cfg = get_persona_config(persona_name)
            self.default_indicators = cfg.get("quant_overrides", {}).get("default_indicators", ["MA", "MACD", "RSI"])
        else:
            self.default_indicators = ["MA", "MACD", "RSI"]

    def analyze_stock(self, code: str, indicators: List[str] | None = None) -> Dict[str, Any]:
        indicators = indicators or self.default_indicators

        df_price = self.db.get_daily(code)
        if df_price.empty:
            return {"error": f"No price data found for {code}"}

        df_price = df_price.sort_values("trade_date")

        results = {}
        for name in indicators:
            try:
                func = get_indicator(name)
                result = func(df_price)

                if isinstance(result, pd.Series):
                    results[name] = {
                        "current": round(result.iloc[-1], 4) if not pd.isna(result.iloc[-1]) else None,
                        "previous": round(result.iloc[-2], 4) if len(result) > 1 and not pd.isna(result.iloc[-2]) else None,
                        "trend": "up" if result.iloc[-1] > result.iloc[-2] else "down" if result.iloc[-1] < result.iloc[-2] else "flat",
                    }
                elif isinstance(result, dict):
                    results[name] = {
                        key: round(series.iloc[-1], 4) if not pd.isna(series.iloc[-1]) else None
                        for key, series in result.items()
                    }
            except Exception as e:
                results[name] = {"error": str(e)}

        return {
            "code": code,
            "latest_date": str(df_price["trade_date"].iloc[-1]),
            "latest_close": round(df_price["close"].iloc[-1], 4),
            "indicators": results,
        }

    def backtest(self, code: str, start: str, end: str, initial_capital: float = 100000.0) -> Dict[str, Any]:
        df = self.db.get_daily(code, start, end)
        if df.empty:
            return {"error": f"No data for {code} in range {start} ~ {end}"}

        df = df.sort_values("trade_date").reset_index(drop=True)

        # Simple buy-and-hold benchmark
        initial_price = df["close"].iloc[0]
        final_price = df["close"].iloc[-1]
        shares = initial_capital / initial_price
        final_value = shares * final_price

        returns = (final_price - initial_price) / initial_price
        max_price = df["close"].max()
        min_price = df["close"].min()
        max_drawdown = (min_price - max_price) / max_price

        return {
            "code": code,
            "start": str(df["trade_date"].iloc[0]),
            "end": str(df["trade_date"].iloc[-1]),
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(returns * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "trades": 1,
        }

    def get_available_indicators(self) -> Dict[str, Any]:
        return list_indicators()
```

### Step 10.2: Write test

```python
# tests/test_quant/test_api.py
import pytest
import pandas as pd
from unittest.mock import Mock, patch
from quant.api import QuantAPI


@pytest.fixture
def api():
    with patch("quant.api.Database") as MockDB:
        db = Mock()
        MockDB.return_value = db

        with patch("quant.api.discover_indicators"):
            with patch("quant.api.get_persona_config") as mock_cfg:
                mock_cfg.return_value = {"quant_overrides": {"default_indicators": ["MA"]}}
                return QuantAPI("zettaranc")


def test_analyze_stock(api):
    api.db.get_daily.return_value = pd.DataFrame({
        "trade_date": pd.date_range("2024-01-01", periods=30),
        "close": [100 + i * 0.5 for i in range(30)],
    })

    result = api.analyze_stock("000001.SZ")
    assert result["code"] == "000001.SZ"
    assert "indicators" in result


def test_backtest(api):
    api.db.get_daily.return_value = pd.DataFrame({
        "trade_date": pd.date_range("2024-01-01", periods=30),
        "close": [100 + i for i in range(30)],
    })

    result = api.backtest("000001.SZ", "20240101", "20240130")
    assert result["code"] == "000001.SZ"
    assert result["total_return"] > 0
```

### Step 10.3: Run tests

```bash
python -m pytest tests/test_quant/test_api.py -v
```

**Expected:** All tests PASS.

### Step 10.4: Commit

```bash
git add quant/api.py tests/test_quant/test_api.py
git commit -m "feat: quant layer - unified API for analysis and backtest"
```

---

## Task 11: Bridge Layer

**Files:**
- Create: `bridge/__init__.py`
- Create: `bridge/knowledge_bridge.py`
- Create: `bridge/quant_bridge.py`

### Step 11.1: Create bridge/knowledge_bridge.py

```python
#!/usr/bin/env python3
# bridge/knowledge_bridge.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from knowledge.query import query_knowledge, format_results


def main():
    parser = argparse.ArgumentParser(description="Query knowledge base for a persona")
    parser.add_argument("--persona", required=True, help="Persona name")
    parser.add_argument("question", nargs="+", help="Question to ask")
    parser.add_argument("--n-results", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    question = " ".join(args.question)
    results = query_knowledge(question, args.persona, n_results=args.n_results)
    formatted = format_results(results)
    print(formatted)


if __name__ == "__main__":
    main()
```

### Step 11.2: Create bridge/quant_bridge.py

```python
#!/usr/bin/env python3
# bridge/quant_bridge.py
import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quant.api import QuantAPI


def main():
    parser = argparse.ArgumentParser(description="Quantitative analysis bridge")
    parser.add_argument("--persona", default="zettaranc", help="Persona name")
    parser.add_argument("--task", required=True, choices=["analyze", "backtest", "indicators"])
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--start", help="Start date (YYYYMMDD)")
    parser.add_argument("--end", help="End date (YYYYMMDD)")
    parser.add_argument("--indicators", nargs="+", help="Indicators to calculate")
    args = parser.parse_args()

    api = QuantAPI(persona_name=args.persona)

    if args.task == "analyze":
        result = api.analyze_stock(args.code, indicators=args.indicators)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.task == "backtest":
        if not args.start or not args.end:
            print("Error: --start and --end required for backtest")
            sys.exit(1)
        result = api.backtest(args.code, args.start, args.end)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.task == "indicators":
        result = api.get_available_indicators()
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

### Step 11.3: Commit

```bash
git add bridge/
git commit -m "feat: bridge layer - CLI entry points for knowledge and quant"
```

---

## Task 12: Zettaranc Persona

**Files:**
- Create: `personas/zettaranc/SKILL.md`
- Create: `personas/zettaranc/personality.md`
- Create: `personas/zettaranc/overrides.yaml`

### Step 12.1: Create personas/zettaranc/personality.md

```markdown
# Z哥（万千）· 表达 DNA

## 语气特征
- 短句为主，偶尔爆粗（用*文明版*替代）
- 喜欢用反问："这事儿概率大吗？"
- 口头禅："不吹牛逼"、"谁也别吹牛逼"、"这事儿概率不大"

## 节奏特征
- 先给结论，再解释
- 关键数字会重复强调
- 停顿用"..."或换行表示

## 决策框架
- 第一层：概率思维——任何事情先看概率
- 第二层：五层筛子——行业、公司、估值、时机、仓位
- 第三层：卖出纪律——比买入更严格

## 核心价值观
- 不预测，只应对
- 利润是市场给的，都是概率的事儿
- 敬畏市场，保持谦卑
```

### Step 12.2: Create personas/zettaranc/SKILL.md

```markdown
---
name: zettaranc-perspective
description: |
  zettaranc（万千）的思维框架与表达方式。
  用途：作为思维顾问，用 Z 哥的视角分析投资、职业与人生决策。
  当用户提到「用 Z 哥的视角」「Z 哥会怎么看」「万千模式」时使用。
---

# zettaranc（万千）· 思维操作系统

## 角色扮演规则

**此 Skill 激活后，直接以 zettaranc（Z 哥）的身份回应。**

- 用「我」而非「Z 哥会认为...」
- 直接用此人的语气、节奏、词汇回答问题
- 遇到不确定的问题，用此人会有的犹豫方式犹豫

## 回答工作流

### Step 1: 问题分类

收到问题后，先判断类型：

| 类型 | 特征 | 行动 |
|------|------|------|
| 需要事实的问题 | 涉及具体公司/人物/事件 | → 先研究再回答 |
| 纯框架问题 | 抽象价值观、思维方式 | → 直接用心智模型回答 |
| 混合问题 | 用具体案例讨论抽象道理 | → 先获取案例事实，再用框架分析 |

### Step 2: 知识检索

当问题需要知识支撑时：
1. 调用 `python bridge/knowledge_bridge.py --persona zettaranc "问题"`
2. 获取返回的知识片段
3. 将知识片段作为上下文融入回答

### Step 3: 量化分析

当问题涉及具体股票时：
1. 调用 `python bridge/quant_bridge.py --persona zettaranc --task analyze --code 股票代码`
2. 获取技术指标和趋势判断
3. 结合人格框架给出分析（不给具体买卖建议）

### Step 4: 生成回答

融合人格语气 + 知识上下文 + 量化数据，生成最终回答。
```

### Step 12.3: Create personas/zettaranc/overrides.yaml

```yaml
# Empty — using all defaults from registry/personas.yaml
```

### Step 12.4: Commit

```bash
git add personas/
git commit -m "feat: persona layer - Zettaranc role configuration"
```

---

## Task 13: Scripts

**Files:**
- Create: `scripts/setup.py`
- Create: `scripts/sync_knowledge.py`
- Create: `scripts/sync_data.py`

### Step 13.1: Create scripts/setup.py

```python
#!/usr/bin/env python3
# scripts/setup.py
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.db import Database
from knowledge.store import KnowledgeStore


def check_env():
    required = ["DASHSCOPE_API_KEY", "TUSHARE_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"Missing environment variables: {missing}")
        print("Please set them in .env file and run: source .env")
        return False
    return True


def init_data_layer():
    print("Initializing data layer...")
    db = Database()
    tables = db.conn.execute("SHOW TABLES").fetchall()
    print(f"Created tables: {[t[0] for t in tables]}")
    db.close()
    print("Data layer initialized.")


def init_knowledge_layer():
    print("Initializing knowledge layer...")
    store = KnowledgeStore()
    collections = store.list_collections()
    print(f"Existing collections: {collections}")
    print("Knowledge layer initialized.")


def main():
    if not check_env():
        sys.exit(1)

    init_data_layer()
    init_knowledge_layer()
    print("\nSetup complete!")


if __name__ == "__main__":
    main()
```

### Step 13.2: Create scripts/sync_knowledge.py

```python
#!/usr/bin/env python3
# scripts/sync_knowledge.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from knowledge.sync import KnowledgeSyncEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", required=True, help="Knowledge base name")
    args = parser.parse_args()

    engine = KnowledgeSyncEngine()
    try:
        count = engine.sync_knowledge_base(args.kb)
        print(f"Synced {count} chunks")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 13.3: Create scripts/sync_data.py

```python
#!/usr/bin/env python3
# scripts/sync_data.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.sync import SyncEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--persona", default="zettaranc", help="Persona name")
    args = parser.parse_args()

    engine = SyncEngine(persona_name=args.persona)
    try:
        result = engine.sync_stock(args.code)
        print(f"Sync result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 13.4: Commit

```bash
git add scripts/
git commit -m "feat: scripts - setup, knowledge sync, and data sync tools"
```

---

## Task 14: Integration Test

**Files:**
- Create: `tests/test_integration.py`

### Step 14.1: Create integration test

```python
# tests/test_integration.py
import pytest
from pathlib import Path


class TestPersonaXIntegration:
    def test_registry_loading(self):
        from shared.config import get_persona_config, get_knowledge_base_config, get_data_source_config

        persona = get_persona_config("zettaranc")
        assert persona["name"] == "Z哥"

        kb = get_knowledge_base_config("zettaranc")
        assert kb["collection"] == "zettaranc"

        ds = get_data_source_config("tushare")
        assert ds["enabled"] is True

    def test_data_layer_initialization(self):
        from data.db import Database
        db = Database(":memory:")
        tables = db.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "daily_prices" in table_names
        db.close()

    def test_quant_indicator_discovery(self):
        from quant.registry import discover_indicators, list_indicators
        discover_indicators()
        indicators = list_indicators()
        assert "MA" in indicators
        assert "MACD" in indicators
        assert "RSI" in indicators

    def test_knowledge_chunker(self):
        from knowledge.chunker import MarkdownChunker
        chunker = MarkdownChunker()
        text = "# Title\n\nContent.\n\n## Section\n\nMore content."
        chunks = chunker.split_text(text)
        assert len(chunks) >= 2
```

### Step 14.2: Run integration tests

```bash
python -m pytest tests/test_integration.py -v
```

**Expected:** All tests PASS.

### Step 14.3: Commit

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for all layers"
```

---

## Task 15: Final Verification

### Step 15.1: Run all tests

```bash
cd /home/chenlei/001_AI/personax
python -m pytest tests/ -v --tb=short
```

**Expected:** All tests PASS.

### Step 15.2: Verify project structure

```bash
find . -type f -not -path "./.git/*" -not -path "*/__pycache__/*" | sort
```

**Expected:** All planned files exist.

### Step 15.3: Final commit

```bash
git add .
git commit -m "feat: PersonaX MVP complete - layered architecture with Registry"
```

---

## Post-MVP Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Configure environment: `cp .env.example .env` and fill in keys
- [ ] Initialize database: `python scripts/setup.py`
- [ ] Sync knowledge base: `python scripts/sync_knowledge.py --kb zettaranc`
- [ ] Sync stock data: `python scripts/sync_data.py --code 000001.SZ`
- [ ] Test knowledge query: `python bridge/knowledge_bridge.py --persona zettaranc "估值方法"`
- [ ] Test quant analysis: `python bridge/quant_bridge.py --persona zettaranc --task analyze --code 000001.SZ`

---

*Plan complete*
