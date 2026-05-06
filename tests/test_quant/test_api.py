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
