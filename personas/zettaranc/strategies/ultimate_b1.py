"""Ultimate B1 Screener (终极B1选股器).

Concept: Combines multiple filters to find the best B1 opportunities.
Filters out stocks that are in wrong wave or have poor structure.

Ultimate B1 Conditions:
1. White above yellow (白上黄上)
2. B1 signal (J < 13)
3. Price above yellow line
4. Not in third wave (not after two recent highs)

Usage:
    from personas.zettaranc.strategies import UltimateB1Strategy
    signal = UltimateB1Strategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import kdj, bbi
from orchestration.models import StrategySignal


@dataclass
class UltimateB1Strategy:
    """Ultimate B1 stock screener."""

    name = "ultimate_b1"

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Detect ultimate B1 signal."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # White line (double smoothed EMA)
        white = close.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

        # Yellow line
        ma14 = close.rolling(window=14).mean()
        ma28 = close.rolling(window=28).mean()
        ma57 = close.rolling(window=57).mean()
        ma114 = close.rolling(window=114).mean()
        yellow = (ma14 + ma28 + ma57 + ma114) / 4

        # Condition 1: White above yellow
        white_above_yellow = white > yellow

        # Condition 2: B1 signal (J < 13)
        kdj_result = kdj.compute(df)
        j = kdj_result.data["J"]
        b1_signal = j < 13

        # Condition 3: Price above yellow
        price_above_yellow = close > yellow

        # Condition 4: Not third wave
        # Count recent local maxima in last 30 days
        is_local_max = (
            (close > close.shift(1))
            & (close > close.shift(2))
            & (close > close.shift(-1))
            & (close > close.shift(-2))
        )
        recent_peaks = is_local_max.rolling(window=30).sum().fillna(0)
        not_third_wave = recent_peaks < 2

        # Combine
        ultimate_b1 = white_above_yellow & b1_signal & price_above_yellow & not_third_wave
        current = ultimate_b1.iloc[-1]

        conditions_met = []
        conditions_failed = []

        if white_above_yellow.iloc[-1]:
            conditions_met.append("白上黄上")
        else:
            conditions_failed.append("白线未在黄线上方")

        if b1_signal.iloc[-1]:
            conditions_met.append("B1信号(J<13)")
        else:
            conditions_failed.append(f"J={j.iloc[-1]:.1f}未<13")

        if price_above_yellow.iloc[-1]:
            conditions_met.append("价格在黄线上方")
        else:
            conditions_failed.append("价格未在黄线上方")

        if not_third_wave.iloc[-1]:
            conditions_met.append("非第三浪")
        else:
            conditions_failed.append("处于第三浪")

        if current:
            return StrategySignal(
                action="buy",
                confidence=0.85,
                reason=f"终极B1: {', '.join(conditions_met)}",
                metadata={
                    "j_value": j.iloc[-1],
                    "white_above_yellow": white_above_yellow.iloc[-1],
                    "conditions_met": conditions_met,
                },
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason=f"无终极B1: {', '.join(conditions_failed)}",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return UltimateB1Strategy().detect(df)
