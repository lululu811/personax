"""Super B1 Strategy (超级B1).

Super B1 = Advanced B1 after extreme shakeout
Concept: After a violent shakeout (heavy volume bearish candle), volume dries up,
KDJ goes deeply negative. This is a high-risk, high-reward entry.

Key principle: "放量可以作假，缩量骗不了人"
(Volume surge can be faked, but volume shrinkage cannot)

Super B1 Conditions:
1. N-shaped structure intact (higher lows)
2. Breathing structure: exhale (volume up + price up) → inhale (volume down + price down)
3. Sudden heavy volume bearish candle (shakeout)
4. Volume shrinks after shakeout
5. J deeply negative (J < -10)

Usage:
    from personas.zettaranc.strategies import SuperB1Strategy
    signal = SuperB1Strategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import kdj
from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class SuperB1Strategy:
    """Super B1 - advanced shakeout signal."""

    name = "super_b1"

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Detect Super B1 signal."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["vol"]

        # KDJ J value
        kdj_result = kdj.compute(df)
        j = kdj_result.data["J"]

        # Condition 1: N-shaped structure - higher lows
        recent_lows = low.rolling(window=20).min()
        prev_recent_lows = recent_lows.shift(10)
        higher_lows = recent_lows > prev_recent_lows

        # Condition 2: Breathing structure
        vol_avg = volume.rolling(window=10).mean()
        exhale = (close > close.shift(1)) & (volume > vol_avg)
        inhale = (close < close.shift(1)) & (volume < vol_avg * 0.7)
        has_breathing = (exhale.rolling(window=10).sum() >= 1) & (inhale.rolling(window=10).sum() >= 1)

        # Condition 3: Shakeout (heavy volume bearish candle)
        avg_vol_20 = volume.rolling(window=20).mean()
        heavy_volume = volume >= avg_vol_20 * 2.0
        bearish = close < open_
        significant_decline = (open_ - close) / open_ * 100 >= 2.0
        shakeout = heavy_volume & bearish & significant_decline
        has_shakeout = shakeout.rolling(window=5).max().fillna(False)

        # Condition 4: Volume shrinks after shakeout
        volume_shrinks = volume < avg_vol_20 * 0.8

        # Condition 5: J deeply negative
        j_deep_negative = j < -10

        # Combined
        super_b1 = has_breathing & has_shakeout & volume_shrinks & j_deep_negative & higher_lows
        current = super_b1.iloc[-1]

        conditions_met = []
        conditions_failed = []

        if higher_lows.iloc[-1]:
            conditions_met.append("N型结构")
        else:
            conditions_failed.append("无N型结构")

        if has_breathing.iloc[-1]:
            conditions_met.append("呼吸结构")
        else:
            conditions_failed.append("无呼吸结构")

        if has_shakeout.iloc[-1]:
            conditions_met.append("暴力震仓")
        else:
            conditions_failed.append("无暴力震仓")

        if volume_shrinks.iloc[-1]:
            conditions_met.append("缩量确认")
        else:
            conditions_failed.append("量未缩")

        if j_deep_negative.iloc[-1]:
            conditions_met.append(f"J={j.iloc[-1]:.1f}<-10")
        else:
            conditions_failed.append(f"J={j.iloc[-1]:.1f}>=-10")

        if current:
            return StrategySignal(
                action="buy",
                confidence=0.8,
                reason=f"超级B1: {', '.join(conditions_met)}",
                metadata={"j_value": j.iloc[-1], "conditions_met": conditions_met},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason=f"无超级B1: {', '.join(conditions_failed)}",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return SuperB1Strategy().detect(df)
