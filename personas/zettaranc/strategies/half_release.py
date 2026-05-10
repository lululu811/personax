"""Half Position Release Strategy (半仓释放).

Concept: When white line deviates too far from yellow line,
it indicates overbought condition - reduce position by half.

White line: EMA of EMA (double smoothed)
Yellow line: (MA14 + MA28 + MA57 + MA114) / 4

When distance > threshold (default 8%):
- Mid-position: consider reducing
- High-position: must reduce

Usage:
    from personas.zettaranc.strategies import HalfReleaseStrategy
    signal = HalfReleaseStrategy().detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from orchestration.models import StrategySignal


@dataclass
class HalfReleaseStrategy:
    """Half position release - overbought warning."""

    name = "half_release"

    def detect(
        self,
        df: pd.DataFrame,
        distance_threshold: float = 8.0,
    ) -> StrategySignal:
        """Detect half release signal.

        Args:
            df: DataFrame with OHLCV
            distance_threshold: Percentage deviation threshold (default 8%)
        """
        close = df["close"]

        # White line (double smoothed EMA)
        white = close.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

        # Yellow line
        ma14 = close.rolling(window=14).mean()
        ma28 = close.rolling(window=28).mean()
        ma57 = close.rolling(window=57).mean()
        ma114 = close.rolling(window=114).mean()
        yellow = (ma14 + ma28 + ma57 + ma114) / 4

        # Distance
        distance = (white - yellow) / yellow * 100
        current_distance = distance.iloc[-1]

        if current_distance > distance_threshold:
            return StrategySignal(
                action="halve",
                confidence=0.65,
                reason=f"半仓释放: 白黄距离{current_distance:.1f}%超过阈值{distance_threshold}%",
                metadata={
                    "distance_pct": current_distance,
                    "threshold": distance_threshold,
                    "white": white.iloc[-1],
                    "yellow": yellow.iloc[-1],
                },
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无半仓释放信号",
            metadata={},
        )


def detect(df: pd.DataFrame) -> StrategySignal:
    return HalfReleaseStrategy().detect(df)
