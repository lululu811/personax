"""Bollinger Bands Technical Indicator.

Standard Bollinger Bands formula:
    MID = SMA(CLOSE, N)
    UPPER = MID + K * STD(CLOSE, N)
    LOWER = MID - K * STD(CLOSE, N)

Usage:
    from tools.quant.technical import bollinger
    result = bollinger.compute(df)
    print(result.data["upper"])
    print(result.signals["below_lower"])  # Price below lower band
"""

import pandas as pd
from dataclasses import dataclass

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    TechnicalTool,
    register_tool,
)


@register_tool
@dataclass
class BollingerTool:
    """Bollinger Bands indicator."""

    name: str = "bollinger"
    description: str = "Bollinger Bands (20, 2)"
    period: int = 20
    k: float = 2.0

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close

        # Calculate bands
        mid = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        upper = mid + self.k * std
        lower = mid - self.k * std

        # Bandwidth and %B
        bandwidth = (upper - lower) / mid * 100
        percent_b = (close - lower) / (upper - lower)

        # Signals
        signals = {
            "above_upper": close > upper,
            "below_lower": close < lower,
            "in_band": (close >= lower) & (close <= upper),
        }

        return ToolResult(
            tool_name=self.name,
            data={
                "upper": upper,
                "mid": mid,
                "lower": lower,
                "bandwidth": bandwidth,
                "percent_b": percent_b,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"period": self.period, "k": self.k},
                "description": {
                    "above_upper": "Price above upper band (overbought)",
                    "below_lower": "Price below lower band (oversold)",
                    "in_band": "Price within bands",
                }
            }
        )


def compute(df: pd.DataFrame, period: int = 20, k: float = 2.0) -> ToolResult:
    """Compute Bollinger Bands."""
    return BollingerTool(period=period, k=k).compute(df)


bollinger = BollingerTool()
