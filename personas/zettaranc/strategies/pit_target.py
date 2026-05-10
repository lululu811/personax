"""Pit Target Strategy (坑口战法).

Concept: Golden pit detection and target price calculation.
"坑向上计算目标价位的公式 = 颈线 * 2 - 坑底"

Golden pit characteristics:
1. Price falls significantly from a neckline level (at least 20% decline)
2. Forms a bottom and stabilizes (consolidation at pit bottom)
3. Volume dries up at the bottom (缩量企稳)
4. When price breaks above neckline, target is calculated

Returns target price and current progress.

Usage:
    from personas.zettaranc.strategies import PitTargetStrategy
    result = PitTargetStrategy().analyze(df)
    print(f"Target: {result.target_price}, Progress: {result.progress_pct}%")
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from orchestration.models import StrategySignal


@dataclass
class PitTargetResult:
    """Result of pit target analysis."""
    in_pit: bool
    stabilization: bool
    pit_signal: bool
    above_neckline: bool
    neckline: float
    pit_bottom: float
    target_price: float
    progress_pct: float


@dataclass
class PitTargetStrategy:
    """Pit strategy - golden pit and target price."""

    name = "pit_target"

    def analyze(self, df: pd.DataFrame, lookback: int = 60) -> PitTargetResult:
        """Analyze pit target pattern.

        Args:
            df: DataFrame with OHLCV
            lookback: Days to look back for neckline (default 60)

        Returns:
            PitTargetResult with signals and target price
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["vol"]

        # Find neckline (recent significant high before decline)
        recent_high = high.rolling(window=lookback).max()
        recent_low = low.rolling(window=lookback).min()

        # Decline from high (at least 20% to be considered a pit)
        decline_pct = (recent_high - close) / recent_high * 100
        in_pit = decline_pct >= 20

        # Volume dries up at bottom
        avg_volume = volume.rolling(window=20).mean()
        volume_dry = volume < avg_volume * 0.5

        # Pit bottom stabilization
        near_bottom = (close <= recent_low * 1.05) & (close >= recent_low * 0.98)
        stabilization = near_bottom & volume_dry

        # Breakout above neckline
        above_neckline = close > recent_high.shift(5) * 0.98

        # Target price: Target = Neckline * 2 - PitBottom
        pit_bottom = recent_low
        neckline = recent_high.shift(lookback // 2)
        target_price = neckline * 2 - pit_bottom

        # Current progress toward target
        progress_pct = (close - pit_bottom) / (target_price - pit_bottom) * 100
        progress_pct = progress_pct.where(target_price > pit_bottom, 0)

        # Pit signal
        pit_signal = in_pit & stabilization

        return PitTargetResult(
            in_pit=bool(in_pit.iloc[-1]),
            stabilization=bool(stabilization.iloc[-1]),
            pit_signal=bool(pit_signal.iloc[-1]),
            above_neckline=bool(above_neckline.iloc[-1]),
            neckline=float(neckline.iloc[-1]) if not neckline.iloc[-1] != neckline.iloc[-1] else 0.0,
            pit_bottom=float(pit_bottom.iloc[-1]),
            target_price=float(target_price.iloc[-1]) if not pd.isna(target_price.iloc[-1]) else 0.0,
            progress_pct=float(progress_pct.iloc[-1]) if not pd.isna(progress_pct.iloc[-1]) else 0.0,
        )

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Alias with StrategySignal return type."""
        result = self.analyze(df)

        if result.pit_signal:
            return StrategySignal(
                action="buy",
                confidence=0.7,
                reason=f"黄金坑信号: 目标价{result.target_price:.2f}, 已完成{result.progress_pct:.1f}%",
                metadata={
                    "target_price": result.target_price,
                    "progress_pct": result.progress_pct,
                    "pit_bottom": result.pit_bottom,
                },
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无坑口信号",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return PitTargetStrategy().detect(df)
