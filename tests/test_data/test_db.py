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
    assert "daily_basic" in table_names
    assert "income" in table_names
    assert "balancesheet" in table_names
    assert "cashflow" in table_names
    assert "fina_indicator" in table_names
    assert "adj_factor" in table_names
    assert "watchlist" in table_names
    assert "holdings" in table_names
    assert "trades" in table_names


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


def test_insert_and_get_daily_basic(db):
    df = pd.DataFrame({
        "code": ["000001.SZ"],
        "trade_date": [pd.Timestamp("2024-01-01")],
        "close": [10.5],
        "turnover_rate": [2.5],
        "pe": [15.2],
        "pb": [1.8],
        "total_mv": [5000000.0],
        "source": ["test"],
    })
    db.insert("daily_basic", df)

    result = db.get_daily_basic("000001.SZ")
    assert len(result) == 1
    assert result.iloc[0]["pe"] == 15.2


def test_insert_and_get_fina_indicator(db):
    df = pd.DataFrame({
        "code": ["000001.SZ"],
        "report_date": [pd.Timestamp("2024-03-31")],
        "report_type": ["Q1"],
        "eps": [0.85],
        "roe": [12.5],
        "grossprofit_margin": [35.2],
        "netprofit_margin": [18.5],
        "source": ["test"],
    })
    db.insert("fina_indicator", df)

    result = db.get_fina_indicator("000001.SZ")
    assert len(result) == 1
    assert result.iloc[0]["roe"] == 12.5


def test_insert_and_get_adj_factor(db):
    df = pd.DataFrame({
        "code": ["000001.SZ"],
        "trade_date": [pd.Timestamp("2024-01-01")],
        "adj_factor": [1.2345],
        "source": ["test"],
    })
    db.insert("adj_factor", df)

    result = db.get_adj_factor("000001.SZ")
    assert len(result) == 1
    assert result.iloc[0]["adj_factor"] == 1.2345


def test_get_last_report_date(db):
    df = pd.DataFrame({
        "code": ["000001.SZ", "000001.SZ"],
        "report_date": [pd.Timestamp("2024-03-31"), pd.Timestamp("2024-06-30")],
        "report_type": ["Q1", "Q2"],
        "basic_eps": [0.5, 1.0],
        "source": ["test", "test"],
    })
    db.insert("income", df)

    last_date = db.get_last_trade_date("000001.SZ", "income")
    assert last_date == "20240630"


def test_watchlist(db):
    db.add_watchlist("000001.SZ", name="平安银行", category="银行", notes="观察")
    db.add_watchlist("000002.SZ", name="万科A", category="地产")

    result = db.get_watchlist()
    assert len(result) == 2
    assert result.iloc[0]["status"] == "active"

    db.remove_watchlist("000001.SZ")
    result = db.get_watchlist(status="active")
    assert len(result) == 1
    assert result.iloc[0]["code"] == "000002.SZ"


def test_holdings(db):
    db.update_holding("000001.SZ", shares=1000, avg_cost=10.5, current_price=11.2, sector="银行")
    result = db.get_holdings()
    assert len(result) == 1
    assert result.iloc[0]["shares"] == 1000
    assert result.iloc[0]["status"] == "holding"

    # Partial sell
    db.update_holding("000001.SZ", shares=500, avg_cost=10.5, current_price=11.2)
    result = db.get_holdings()
    assert result.iloc[0]["shares"] == 500

    # Close position
    db.update_holding("000001.SZ", shares=0, avg_cost=10.5)
    result = db.get_holdings(status="closed")
    assert len(result) == 1


def test_trades(db):
    db.add_trade("2024-01-01", "000001.SZ", "BUY", 1000, 10.5, fee=5, tax=0, name="平安银行")
    db.add_trade("2024-06-01", "000001.SZ", "SELL", 500, 11.2, fee=5, tax=5.6)

    result = db.get_trades()
    assert len(result) == 2
    assert result.iloc[0]["trade_type"] == "SELL"
    assert result.iloc[0]["status"] == "confirmed"

    result = db.get_trades(code="000001.SZ")
    assert len(result) == 2

    result = db.get_trades(start_date="2024-01-01", end_date="2024-03-01")
    assert len(result) == 1
    assert result.iloc[0]["trade_type"] == "BUY"
