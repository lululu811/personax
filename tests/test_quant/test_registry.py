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
