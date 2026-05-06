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
