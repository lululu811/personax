"""Stochastic Oscillator (Single Needle) Technical Indicator.

Zettaranc's "single needle" uses 4 stochastic lines:
    Short-term (white):  100*(C-LLV(L,N1))/(HHV(H,N1)-LLV(L,N1))
    Medium-term (yellow): 100*(C-LLV(L,10))/(HHV(H,10)-LLV(L,10))
    Mid-long-term (purple): 100*(C-LLV(L,20))/(HHV(H,20)-LLV(L,20))
    Long-term (red): 100*(C-LLV(L,N2))/(HHV(H,N2)-LLV(L,N2))

Usage:
    from tools.quant.technical import stochastic
    result = stochastic.compute(df)
    print(result.data["short"])   # Short-term line
    print(result.signals["four_zero"])  # All <= 6
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
class StochasticTool:
    """Multi-period stochastic indicator (Zettaranc's single needle)."""

    name: str = "stochastic"
    description: str = "Multi-period stochastic (Zettaranc single needle)"
    n1: int = 5   # Short-term period
    n2: int = 60  # Long-term period

    def _stochastic(self, close: pd.Series, high: pd.Series, low: pd.Series, n: int) -> pd.Series:
        ll = low.rolling(window=n, min_periods=1).min()
        hh = high.rolling(window=n, min_periods=1).max()
        return (close - ll) / (hh - ll) * 100

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close
        high = data.high
        low = data.low

        # Calculate 4 stochastic lines
        short = self._stochastic(close, high, low, self.n1)        # white
        medium = self._stochastic(close, high, low, 10)             # yellow
        mid_long = self._stochastic(close, high, low, 20)          # purple
        long_term = self._stochastic(close, high, low, self.n2)    # red

        # Signals
        signals = {
            "four_zero": (short <= 6) & (medium <= 6) & (mid_long <= 6) & (long_term <= 6),
            "white_below_20": (short <= 20) & (long_term >= 60),
        }

        # Cross detection
        short_above_long = short > long_term
        short_above_medium = short > medium

        signals["white_cross_red"] = (
            (short_above_long.shift(1).fillna(False).eq(False)) & short_above_long & (long_term < 20)
        )
        signals["white_cross_yellow"] = (
            (short_above_medium.shift(1).fillna(False).eq(False)) & short_above_medium & (medium < 30)
        )

        return ToolResult(
            tool_name=self.name,
            data={
                "short": short,
                "medium": medium,
                "mid_long": mid_long,
                "long": long_term,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"n1": self.n1, "n2": self.n2},
                "description": {
                    "four_zero": "All lines <= 6 (extreme oversold)",
                    "white_below_20": "Short <= 20 AND Long >= 60",
                    "white_cross_red": "Short crosses above Long below 20",
                    "white_cross_yellow": "Short crosses above Medium below 30",
                }
            }
        )


def compute(df: pd.DataFrame, n1: int = 5, n2: int = 60) -> ToolResult:
    """Compute multi-period stochastic."""
    return StochasticTool(n1=n1, n2=n2).compute(df)


stochastic = StochasticTool()
