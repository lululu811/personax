"""Single Needle Below 20 Strategy (单针下20 / 补票战法).

Concept: The "deep V" reversal pattern.
White line (short-term stochastic) quickly V-bounces from below 20 to 100,
while red line (long-term) stays elevated (>80).

Single Needle 20 Conditions:
1. Long-term (red) >= 80 for 5 consecutive days
2. Long-term >= 99.99 today (long line at 100)
3. Short-term >= 99.99 today (white line at 100)
4. Short-term <= 20 yesterday (white was below 20 yesterday)

This is the core signal for 补票战法 (ticket replenishment strategy).

Usage:
    from personas.zettaranc.strategies import SingleNeedle20Strategy
    signal = SingleNeedle20Strategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import stochastic
from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class SingleNeedle20Strategy:
    """Single needle below 20 - deep V reversal."""

    name = "single_needle_20"

    def detect(self, df: pd.DataFrame, n1: int = 5, n2: int = 60) -> StrategySignal:
        """Detect single needle 20 signal.

        Args:
            df: DataFrame with OHLCV
            n1: Short-term period (default 5)
            n2: Long-term period (default 60)
        """
        close = df["close"]
        low = df["low"]

        # Short-term and long-term stochastic
        stoch_result = stochastic.compute(df, n1=n1, n2=n2)
        short = stoch_result.data["short"]
        long_term = stoch_result.data["long"]

        # Condition 1: Long-term >= 80 for 5 consecutive days
        long_above_80 = long_term >= 80
        long_5days = long_above_80.rolling(window=5).min().astype(bool)

        # Condition 2: Long-term >= 99.99 today
        long_near_100 = long_term >= 99.99

        # Condition 3: Short-term >= 99.99 today
        short_near_100 = short >= 99.99

        # Condition 4: Short-term <= 20 yesterday
        short_below_20_yesterday = short.shift(1) <= 20

        # Combined signal (ensure all are boolean)
        signal = long_5days.astype(bool) & long_near_100.astype(bool) & short_near_100.astype(bool) & short_below_20_yesterday.astype(bool)
        current = signal.iloc[-1]

        conditions_met = []
        conditions_failed = []

        if long_5days.iloc[-1]:
            conditions_met.append("长线5日≥80")
        else:
            conditions_failed.append("长线5日未≥80")

        if long_near_100.iloc[-1]:
            conditions_met.append("长线=100")
        else:
            conditions_failed.append(f"长线={long_term.iloc[-1]:.1f}≠100")

        if short_near_100.iloc[-1]:
            conditions_met.append("白线=100")
        else:
            conditions_failed.append(f"白线={short.iloc[-1]:.1f}≠100")

        if short_below_20_yesterday.iloc[-1]:
            conditions_met.append("白线昨≤20")
        else:
            conditions_failed.append(f"白线昨={short.shift(1).iloc[-1]:.1f}>20")

        if current:
            return StrategySignal(
                action="buy",
                confidence=0.85,
                reason=f"单针下20补票信号: {', '.join(conditions_met)}",
                metadata={
                    "short": short.iloc[-1],
                    "long": long_term.iloc[-1],
                    "short_yesterday": short.shift(1).iloc[-1],
                },
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason=f"无单针下20: {', '.join(conditions_failed)}",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return SingleNeedle20Strategy().detect(df)
