"""BBI (Bull and Bear Index) Technical Indicator.

BBI Formula:
    BBI = (MA3 + MA6 + MA12 + MA24) / 4

Usage:
    from tools.quant.technical import bbi
    result = bbi.compute(df)
    print(result.data["bbi"])
    print(result.signals["above_bbi"])  # price above BBI
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
class BBITool:
    """BBI (Bull and Bear Index) - multi-moving-average trend indicator."""

    name: str = "bbi"
    description: str = "BBI multi-MA trend indicator"
    periods: tuple = (3, 6, 12, 24)

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close

        # Calculate component MAs
        ma3 = close.rolling(window=3).mean()
        ma6 = close.rolling(window=6).mean()
        ma12 = close.rolling(window=12).mean()
        ma24 = close.rolling(window=24).mean()

        # BBI
        bbi = (ma3 + ma6 + ma12 + ma24) / 4

        # Signals
        signals = {
            "above_bbi": close > bbi,           # Bullish
            "below_bbi": close < bbi,           # Bearish
        }

        return ToolResult(
            tool_name=self.name,
            data={
                "bbi": bbi,
                "ma3": ma3,
                "ma6": ma6,
                "ma12": ma12,
                "ma24": ma24,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"periods": self.periods},
                "description": {
                    "above_bbi": "Close above BBI (bullish trend)",
                    "below_bbi": "Close below BBI (bearish trend)",
                }
            }
        )


def compute(df: pd.DataFrame) -> ToolResult:
    """Compute BBI indicator."""
    return BBITool().compute(df)


bbi = BBITool()
