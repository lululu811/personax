"""KDJ (Stochastic) Technical Indicator.

Standard KDJ formula:
    RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    K = SMA(RSV, M1, 1)
    D = SMA(K, M2, 1)
    J = 3*K - 2*D

Usage:
    from tools.quant.technical import kdj
    result = kdj.compute(df)
    print(result.data["J"])       # J values
    print(result.signals["b1"])   # J < 13 signal
"""

import pandas as pd
from dataclasses import dataclass, field

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    SignalType,
    TechnicalTool,
    register_tool,
)


@register_tool
@dataclass
class KDJTool:
    """KDJ (Stochastic) indicator with configurable parameters."""

    name: str = "kdj"
    description: str = "KDJ stochastic indicator with J-value signals"
    n: int = 9   # RSV lookback period
    m1: int = 3  # K smoothing
    m2: int = 3  # D smoothing

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            data = OHLCV.from_dataframe(data)

        close = data.close
        high = data.high
        low = data.low

        # Calculate RSV
        lowest_low = low.rolling(window=self.n, min_periods=1).min()
        highest_high = high.rolling(window=self.n, min_periods=1).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(0)

        # Calculate K, D, J
        k = rsv.rolling(window=self.m1).mean()
        d = k.rolling(window=self.m2).mean()
        j = 3 * k - 2 * d

        # Named signals
        k_above_d = k > d
        k_below_d = k < d

        signals = {
            "b1": j < 13,                      # General oversold
            "b1_strict": j < -10,             # Conservative / young-wife style
            "overbought": j > 80,              # Overbought warning
            "golden_cross": (
                k_below_d.shift(1).fillna(False) & k_above_d
            ),                                  # K crosses above D
            "dead_cross": (
                k_above_d.shift(1).fillna(False) & k_below_d
            ),                                  # K crosses below D
        }

        return ToolResult(
            tool_name=self.name,
            data={
                "K": k,
                "D": d,
                "J": j,
                "RSV": rsv,
            },
            signals={k: bool(v.iloc[-1]) if hasattr(v, 'iloc') else bool(v) for k, v in signals.items()},
            metadata={
                "params": {"n": self.n, "m1": self.m1, "m2": self.m2},
                "description": {
                    "b1": "J < 13 (general oversold)",
                    "b1_strict": "J < -10 (conservative)",
                    "overbought": "J > 80",
                    "golden_cross": "K crosses above D",
                    "dead_cross": "K crosses below D",
                }
            }
        )


# Convenience function
def compute(
    df: pd.DataFrame,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> ToolResult:
    """Compute KDJ indicator."""
    tool = KDJTool(n=n, m1=m1, m2=m2)
    return tool.compute(df)


# Module-level singleton for registry
kdj = KDJTool()
