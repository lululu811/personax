"""RSI (Relative Strength Index) Technical Indicator.

Standard RSI formula:
    RS = SMA(UP, N) / SMA(DOWN, N)
    RSI = 100 - 100 / (1 + RS)

Zettaranc settings (period=3):
    - RSI < 20: recent low, potential buy point
    - RSI > 80: recent high, potential sell point

Usage:
    from tools.quant.technical import rsi_3
    result = rsi_3.compute(df)
    print(result.signals["oversold"])  # True if RSI < 20
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
class RSITool:
    """RSI indicator with configurable period and oversold/overbought thresholds."""

    name: str = "rsi_3"
    description: str = "RSI with 20/80 boundaries (Zettaranc settings: period=3)"
    period: int = 3
    oversold_threshold: float = 20.0
    overbought_threshold: float = 80.0

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close

        # Price changes
        delta = close.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # Average gain and loss using SMA
        avg_gain = gain.rolling(window=self.period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=1).mean()

        # RS and RSI
        rs = avg_gain / avg_loss
        rs = rs.replace([float('inf'), -float('inf')], 0)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)

        # Signals
        signals = {
            "oversold": rsi < self.oversold_threshold,
            "overbought": rsi > self.overbought_threshold,
            "neutral": (rsi >= self.oversold_threshold) & (rsi <= self.overbought_threshold),
        }

        return ToolResult(
            tool_name=self.name,
            data={"rsi": rsi},
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {
                    "period": self.period,
                    "oversold_threshold": self.oversold_threshold,
                    "overbought_threshold": self.overbought_threshold,
                },
                "description": {
                    "oversold": f"RSI < {self.oversold_threshold} (buy zone)",
                    "overbought": f"RSI > {self.overbought_threshold} (sell zone)",
                }
            }
        )


def compute(df: pd.DataFrame, period: int = 3) -> ToolResult:
    """Compute RSI indicator."""
    tool = RSITool(period=period)
    return tool.compute(df)


rsi_3 = RSITool()
