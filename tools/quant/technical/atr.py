"""ATR (Average True Range) Technical Indicator.

True Range = MAX(HIGH - LOW, ABS(HIGH - PREV_CLOSE), ABS(LOW - PREV_CLOSE))
ATR = SMA(TR, N)

Usage:
    from tools.quant.technical import atr
    result = atr.compute(df)
    print(result.data["atr"])
    print(result.signals["high_volatility"])  # ATR > threshold
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
class ATRTool:
    """ATR (Average True Range) volatility indicator."""

    name: str = "atr"
    description: str = "Average True Range volatility"
    period: int = 14

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        high = data.high
        low = data.low
        close = data.close

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR
        atr = tr.rolling(window=self.period, min_periods=1).mean()

        # ATR as percentage of close (normalized volatility)
        atr_pct = atr / close * 100

        # Signals
        signals = {
            "high_volatility": atr_pct > atr_pct.rolling(50).mean() * 1.5,
            "low_volatility": atr_pct < atr_pct.rolling(50).mean() * 0.5,
        }

        return ToolResult(
            tool_name=self.name,
            data={
                "atr": atr,
                "tr": tr,
                "atr_pct": atr_pct,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"period": self.period},
                "description": {
                    "high_volatility": "ATR% above recent 50-day average * 1.5",
                    "low_volatility": "ATR% below recent 50-day average * 0.5",
                }
            }
        )


def compute(df: pd.DataFrame, period: int = 14) -> ToolResult:
    """Compute ATR indicator."""
    return ATRTool(period=period).compute(df)


atr = ATRTool()
