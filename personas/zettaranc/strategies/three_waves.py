"""Three Waves Strategy (三波理论).

Concept: Stocks move in three waves - Build, Pull, Sprint.
Each wave has different characteristics and requires different handling.

Wave Types:
1. 建仓波 (Build Wave): Bottom rises with continuous volume, cumulative 25-50%
2. 拉升波 (Pull Wave): Quick脱离建仓成本区, first B1 after pull should be avoided
3. 冲刺波 (Sprint Wave): Final large-scale rise, do not touch after sprint

Key filtering rules:
- First B1 after pull wave: avoid (risky)
- After sprint wave: do not enter
- One-wave flow: no clear build/pull structure, avoid

Usage:
    from personas.zettaranc.strategies import ThreeWavesStrategy
    result = ThreeWavesStrategy().analyze(df)
    print(result.phase)
"""

from dataclasses import dataclass
from typing import Literal
import pandas as pd

from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class ThreeWavesResult:
    """Result of three waves analysis."""
    phase: str              # "build", "pull", "sprint", "one_wave", "unknown"
    build_wave: bool
    pull_wave: bool
    sprint_wave: bool
    one_wave: bool
    avoid_b1: bool
    no_enter: bool


@dataclass
class ThreeWavesStrategy:
    """Three wave theory detector."""

    name = "three_waves"

    def analyze(self, df: pd.DataFrame, lookback: int = 60) -> ThreeWavesResult:
        """Analyze three wave structure."""
        close = df["close"]
        volume = df["vol"]

        # Cumulative gain
        start_price = close.shift(lookback)
        cumulative_gain = (close - start_price) / start_price * 100

        # Volume ratio
        avg_volume = volume.rolling(window=20).mean()
        volume_ratio = volume / avg_volume

        # Build wave detection
        recent_low = close.rolling(window=lookback).min()
        near_bottom = close <= recent_low * 1.15
        high_volume_period = avg_volume > volume.shift(20).rolling(window=20).mean() * 1.5
        build_wave = near_bottom & (cumulative_gain >= 15) & (cumulative_gain <= 50) & high_volume_period

        # Pull wave
        short_gain = (close - close.shift(10)) / close.shift(10) * 100
        rapid_rise = short_gain >= 20
        pull_wave = (~near_bottom) & rapid_rise & (cumulative_gain >= 20) & (cumulative_gain < 50)

        # Sprint wave
        sprint_wave = (cumulative_gain >= 50) & (short_gain >= 15)

        # One-wave flow
        one_wave = (cumulative_gain >= 30) & (~high_volume_period) & (volume_ratio < 1.2)

        # Phase classification
        phase = "unknown"
        if sprint_wave.iloc[-1]:
            phase = "sprint"
        elif pull_wave.iloc[-1] and not sprint_wave.iloc[-1]:
            phase = "pull"
        elif build_wave.iloc[-1]:
            phase = "build"
        elif one_wave.iloc[-1]:
            phase = "one_wave"

        # Trading signals
        after_pull = phase == "pull"
        avoid_b1 = after_pull
        no_enter = sprint_wave.iloc[-1] or one_wave.iloc[-1]

        return ThreeWavesResult(
            phase=phase,
            build_wave=bool(build_wave.iloc[-1]),
            pull_wave=bool(pull_wave.iloc[-1]),
            sprint_wave=bool(sprint_wave.iloc[-1]),
            one_wave=bool(one_wave.iloc[-1]),
            avoid_b1=avoid_b1,
            no_enter=no_enter,
        )

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Alias with StrategySignal return type."""
        result = self.analyze(df)

        if result.sprint_wave:
            return StrategySignal(
                action="sell",
                confidence=0.8,
                reason="冲刺波: 已进入第三浪，不宜再买入",
                metadata={"phase": result.phase},
            )
        elif result.one_wave:
            return StrategySignal(
                action="hold",
                confidence=0.7,
                reason="一波流: 无清晰建仓结构，观望",
                metadata={"phase": result.phase},
            )
        elif result.build_wave:
            return StrategySignal(
                action="buy",
                confidence=0.6,
                reason="建仓波: 处于第一阶段，可关注",
                metadata={"phase": result.phase},
            )
        elif result.pull_wave:
            return StrategySignal(
                action="warning",
                confidence=0.5,
                reason="拉升波: B1后勿追，等待回调",
                metadata={"phase": result.phase},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无法判断所处波段",
            metadata={"phase": "unknown"},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return ThreeWavesStrategy().detect(df)
