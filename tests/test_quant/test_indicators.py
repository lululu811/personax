import pandas as pd
import numpy as np
from quant.indicators.ma import calculate_ma
from quant.registry import discover_indicators, get_indicator


def _make_df():
    np.random.seed(42)
    return pd.DataFrame({
        "close": 100 + np.cumsum(np.random.randn(100)),
        "open": 100 + np.cumsum(np.random.randn(100)),
        "high": 102 + np.cumsum(np.random.randn(100)),
        "low": 98 + np.cumsum(np.random.randn(100)),
        "vol": np.random.randint(1000000, 5000000, 100),
    })


def test_ma():
    df = _make_df()
    ma = calculate_ma(df, window=20)
    assert len(ma) == len(df)
    assert pd.isna(ma.iloc[0])
    assert not pd.isna(ma.iloc[19])


def test_macd_via_registry():
    discover_indicators()
    df = _make_df()

    func = get_indicator("MACD")
    result = func(df)
    assert "dif" in result
    assert "dea" in result
    assert "macd" in result
    assert len(result["dif"]) == len(df)


def test_macd_lowercase_via_registry():
    discover_indicators()
    df = _make_df()

    func = get_indicator("macd")
    result = func(df)
    assert "dif" in result
    assert len(result["dif"]) == len(df)


def test_rsi_via_registry():
    discover_indicators()
    df = _make_df()

    func = get_indicator("RSI")
    result = func(df)
    # New rsi_3 returns data dict with rsi key
    assert len(result) > 0
