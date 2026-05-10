"""S1 Top Warning Strategy (S1顶部警告).

S1 = Sell 1 = First sell signal
Concept: High volume at relative high regardless of candle direction.
This indicates potential distribution.

S1 Conditions:
1. Relative high (within top 15% of last 20 days)
2. Volume significantly higher than recent average (>2.5x)

Trading rule:
- Reduce position by half when S1 appears
- Not a full exit, just a warning to take profits

Usage:
    from personas.zettaranc.strategies import S1WarningStrategy
    signal = S1WarningStrategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from orchestration.models import StrategySignal


@dataclass
class S1WarningStrategy:
    """S1 top warning - distribution signal."""

    name = "s1"

    def detect(
        self,
        df: pd.DataFrame,
        volume_mult: float = 2.5,
        lookback: int = 20,
    ) -> StrategySignal:
        """Detect S1 top warning signal.

        Args:
            df: DataFrame with OHLCV
            volume_mult: Volume multiplier threshold (default 2.5)
            lookback: Days to calculate relative high (default 20)
        """
        close = df["close"]
        volume = df["vol"]

        # Relative high (within top 15% of last lookback days)
        recent_high = close.rolling(window=lookback).max()
        at_relative_high = close >= recent_high * 0.85

        # Volume surge
        avg_volume = volume.rolling(window=lookback).mean()
        volume_surge = volume > avg_volume * volume_mult

        # S1 signal
        s1 = at_relative_high & volume_surge
        current_s1 = s1.iloc[-1]

        if current_s1:
            return StrategySignal(
                action="warning",
                confidence=0.7,
                reason="S1顶部警告: 放量在相对高位，注意减仓",
                metadata={
                    "volume_ratio": volume.iloc[-1] / avg_volume.iloc[-1],
                    "near_high": at_relative_high.iloc[-1],
                },
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无S1信号",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return S1WarningStrategy().detect(df)
