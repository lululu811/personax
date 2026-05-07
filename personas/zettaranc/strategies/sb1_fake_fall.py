"""SB1 Fake Fall Strategy (假摔B1).

SB1 = Shakeout B1 = 震仓B1
Concept: Main force shakes out weak hands with a fake breakdown,
then quickly reverses. This creates a better entry point.

SB1 Conditions:
1. Breaks previous low (诱空 - fake breakdown)
2. Next day strong reversal (收复前低, 阳包阴)
3. Reversal with volume surge (放量确认)

Trading rule:
- Wait for reversal confirmation before entry
- Stop loss at the shakeout low

Usage:
    from personas.zettaranc.strategies import SB1FakeFallStrategy
    signal = SB1FakeFallStrategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class SB1FakeFallStrategy:
    """SB1 fake fall detection - main force shakeout pattern."""

    name = "sb1"

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Detect SB1 fake fall signal.

        Returns signal on the reversal day (after shakeout).
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["vol"]

        # 1. Breaks previous low (today's low < yesterday's low)
        breaks_low = low < low.shift(1)

        # 2. Next day reversal (tomorrow's close > today's open, covers today's high)
        next_day_bullish = close.shift(-1) > open_.shift(-1)
        next_day_covers = close.shift(-1) > high  # Reclaims today's high

        # 3. Next day volume surge
        avg_volume = volume.rolling(window=20).mean()
        next_day_volume = volume.shift(-1) > avg_volume * 1.5

        # Signal on the reversal day (shift back)
        # Today is shakeout, tomorrow is reversal
        signal = (
            breaks_low.shift(1).fillna(False)  # Yesterday was shakeout
            & next_day_bullish.shift(1).fillna(False)  # Today is reversal
            & next_day_covers.shift(1).fillna(False)  # Today covers yesterday
            & next_day_volume.shift(1).fillna(False)  # Today has volume
        )

        current_signal = signal.iloc[-1]

        if current_signal:
            return StrategySignal(
                action="buy",
                confidence=0.75,
                reason="SB1假摔反转: 跌破后次日阳包阴放量确认",
                metadata={"shakeout": True, "reversal": True},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无SB1信号",
            metadata={},
        )


# Convenience function
def detect(df: pd.DataFrame) -> StrategySignal:
    return SB1FakeFallStrategy().detect(df)
