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
