import pandas as pd
from quant.registry import register_indicator


@register_indicator("MA", category="trend")
def calculate_ma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Moving Average"""
    return df["close"].rolling(window=window).mean()
