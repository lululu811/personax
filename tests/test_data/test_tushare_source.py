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
