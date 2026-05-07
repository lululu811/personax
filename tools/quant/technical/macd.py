"""MACD (Moving Average Convergence Divergence) Technical Indicator.

Standard MACD formula:
    DIF = EMA12 - EMA26
    DEA = EMA(DIF, 9)
    MACD = (DIF - DEA) * 2

Usage:
    from tools.quant.technical import macd
    result = macd.compute(df)
    print(result.data["dif"])
    print(result.signals["golden_cross"])  # DIF crosses above DEA
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
class MACDTool:
    """MACD indicator with standard parameters."""

    name: str = "macd"
    description: str = "MACD (12, 26, 9)"
    fast: int = 12
    slow: int = 26
    signal: int = 9

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close

        # Calculate EMAs
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()

        # DIF and DEA
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.signal, adjust=False).mean()

        # MACD histogram
        macd_hist = (dif - dea) * 2

        # Signals
        dif_above_dea = dif > dea
        signals = {
            "golden_cross": (~dif_above_dea.shift(1).fillna(False)) & dif_above_dea,
            "dead_cross": (dif_above_dea.shift(1).fillna(False)) & (~dif_above_dea),
            "above_zero": dif > 0,
            "below_zero": dif < 0,
        }

        return ToolResult(
            tool_name=self.name,
            data={
                "dif": dif,
                "dea": dea,
                "macd": macd_hist,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"fast": self.fast, "slow": self.slow, "signal": self.signal},
                "description": {
                    "golden_cross": "DIF crosses above DEA (bullish)",
                    "dead_cross": "DIF crosses below DEA (bearish)",
                    "above_zero": "DIF above zero (bullish territory)",
                    "below_zero": "DIF below zero (bearish territory)",
                }
            }
        )


def compute(df: pd.DataFrame) -> ToolResult:
    """Compute MACD indicator."""
    return MACDTool().compute(df)


macd = MACDTool()
