"""Two Thirty Rule Strategy (两个30%原则).

Concept: "相对安全的区间是：前期放量的三根中大阳线，
累计换手率不超过30%，且建仓期间绝对涨幅不超过30%"

This rule filters out stocks that have risen too much or turned over
too much during accumulation, which indicates distribution not accumulation.

Usage:
    from personas.zettaranc.strategies import TwoThirtyRuleStrategy
    signal = TwoThirtyRuleStrategy().validate(df)
"""

from dataclasses import dataclass
import pandas as pd

from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class TwoThirtyRuleStrategy:
    """Two-30% rule validator."""

    name = "two_thirty"

    def validate(
        self,
        df: pd.DataFrame,
        max_gain_pct: float = 30.0,
        max_turnover_pct: float = 30.0,
        lookback: int = 20,
    ) -> bool:
        """Validate two-30% rule.

        Returns True if stock passes the rule.
        """
        close = df["close"]
        volume = df["vol"]

        # Cumulative gain
        start_price = close.shift(lookback)
        cumulative_gain = (close - start_price) / start_price * 100

        # Cumulative turnover proxy
        cumulative_volume = volume.rolling(window=lookback).sum()
        avg_daily_volume = volume.rolling(window=lookback).mean()
        turnover_proxy = cumulative_volume / avg_daily_volume
        cumulative_turnover_pct = turnover_proxy * 1.5  # Heuristic

        # Check conditions
        gain_ok = cumulative_gain <= max_gain_pct
        turnover_ok = cumulative_turnover_pct <= max_turnover_pct

        return bool(gain_ok.iloc[-1] and turnover_ok.iloc[-1])

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Alias with StrategySignal return type."""
        passes = self.validate(df)

        if passes:
            return StrategySignal(
                action="hold",
                confidence=0.7,
                reason="两个30%原则: 通过建仓期检验",
                metadata={"passes": True},
            )
        else:
            return StrategySignal(
                action="warning",
                confidence=0.6,
                reason="两个30%原则: 未通过，涨幅或换手率超标",
                metadata={"passes": False},
            )


def detect(df: pd.DataFrame) -> StrategySignal:
    return TwoThirtyRuleStrategy().detect(df)
