"""Abnormal Movement Strategy (异动检测).

Concept: "异动 = 突然放量，价随量升"
Abnormal movement = sudden volume surge + price rises with volume

Key characteristics:
1. Sudden volume surge (>= volume_mult x recent average)
2. Price rises with volume (价随量升)
3. Near or below 60-day MA (60日线底下或者附近的异动越强)
4. 60-day MA turning flat or up (黄线拐头)

After abnormal movement, the subsequent "shrinking volume pullback"
is where B1 opportunities emerge.

Usage:
    from personas.zettaranc.strategies import AbnormalMovementStrategy
    signal = AbnormalMovementStrategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from orchestration.models import StrategySignal


@dataclass
class AbnormalMovementStrategy:
    """Abnormal movement detection."""

    name = "abnormal"

    def detect(
        self,
        df: pd.DataFrame,
        volume_mult: float = 2.0,
        min_gain_pct: float = 3.0,
        lookback: int = 20,
    ) -> StrategySignal:
        """Detect abnormal movement signal.

        Args:
            df: DataFrame with OHLCV
            volume_mult: Volume multiplier (default 2.0)
            min_gain_pct: Minimum gain percentage (default 3.0)
            lookback: Days for volume average (default 20)
        """
        close = df["close"]
        open_ = df["open"]
        volume = df["vol"]

        # 60-day MA
        ma60 = close.rolling(window=60).mean()

        # Volume surge
        avg_volume = volume.rolling(window=lookback).mean()
        volume_surge = volume >= avg_volume * volume_mult

        # Price rises with volume
        gain_pct = (close - open_) / open_ * 100
        price_rises = (close > open_) & (gain_pct >= min_gain_pct)

        # Near or below 60-day MA
        near_ma60 = (close >= ma60 * 0.90) | (close >= ma60)

        # 60-day MA flat or turning up
        ma60_flat_or_up = ma60 >= ma60.shift(5)

        # Combined signal
        abnormal = volume_surge & price_rises & near_ma60 & ma60_flat_or_up
        current = abnormal.iloc[-1]

        conditions_met = []
        conditions_failed = []

        if volume_surge.iloc[-1]:
            conditions_met.append(f"放量{volume.iloc[-1]/avg_volume.iloc[-1]:.1f}倍")
        else:
            conditions_failed.append("量未放")

        if price_rises.iloc[-1]:
            conditions_met.append(f"价升{gain_pct.iloc[-1]:.1f}%")
        else:
            conditions_failed.append("价未配合")

        if near_ma60.iloc[-1]:
            conditions_met.append("贴近60日线")
        else:
            conditions_failed.append("远离60日线")

        if ma60_flat_or_up.iloc[-1]:
            conditions_met.append("60日线向上")
        else:
            conditions_failed.append("60日线向下")

        if current:
            return StrategySignal(
                action="warning",
                confidence=0.6,
                reason=f"异动: {', '.join(conditions_met)}",
                metadata={"volume_ratio": volume.iloc[-1]/avg_volume.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无异动信号",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return AbnormalMovementStrategy().detect(df)
