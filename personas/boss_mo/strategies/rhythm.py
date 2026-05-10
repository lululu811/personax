"""涨一段跌一段节奏检测 (Rhythm Detection).

BOSS墨核心模型：
  市场永远按「涨一段跌一段」的规律运行，没有无限涨也没有无限跌

原理：
  通过识别最近的高点和低点，测量当前趋势段的幅度和时长，
  与历史涨跌段对比，判断当前处于涨跌循环的哪个阶段。

策略判定：
  1. 识别最近的高低点（swing high/low）
  2. 测量当前段的涨幅/跌幅和持续时间
  3. 与历史段的均值对比，判断是否"涨完了"或"跌透了"
  4. 输出当前阶段和下一段预期

Usage:
    from personas.boss_mo.strategies import RhythmStrategy
    strategy = RhythmStrategy()
    result = strategy.detect(df)
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class RhythmResult:
    """Result of rhythm detection."""
    phase: str         # "rising_early", "rising_mid", "rising_late", "falling_early", "falling_mid", "falling_late", "consolidating"
    score: float       # 0.0-1.0, confidence in phase judgment
    reason: str
    details: dict


class RhythmStrategy:
    """BOSS墨涨一段跌一段节奏检测。

    判断当前处于涨跌循环的哪个阶段。
    """

    name = "rhythm"

    def detect(self, df: pd.DataFrame) -> RhythmResult:
        """Detect which phase of the up/down cycle the stock is in.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            RhythmResult with phase classification
        """
        close = df["close"]

        # ---- Identify swing points (高低点识别) ----
        swings = self._find_swing_points(close)

        if len(swings) < 3:
            # Not enough data for cycle analysis
            return RhythmResult(
                phase="consolidating",
                score=0.0,
                reason="数据不足，无法识别完整的涨跌段循环。至少需要 3 个高低点才能判断节奏",
                details={"swing_count": len(swings)},
            )

        # ---- Analyze current trend ----
        current_trend, current_gain, current_days = self._analyze_current_trend(
            close, swings
        )

        # ---- Compare with historical segments ----
        avg_up, avg_down, avg_up_days, avg_down_days = self._segment_stats(swings)

        # ---- Phase judgment ----
        if current_trend == "up":
            if avg_up_days > 0 and current_days / avg_up_days < 0.4:
                phase = "rising_early"
                pct = min(current_days / avg_up_days * 100, 100)
                reason = (
                    f"涨一段早期：当前已涨 {current_gain:.1f}%，持续 {current_days} 天，"
                    f"历史平均涨段涨 {avg_up:.1f}%/{avg_up_days} 天。"
                    f"目前进度约 {pct:.0f}%，刚起步。"
                    f"这就叫涨一段跌一段，现在还在涨的阶段"
                )
                score = min(current_days / avg_up_days, 1.0) * 0.8
            elif avg_up_days > 0 and current_days / avg_up_days < 0.75:
                phase = "rising_mid"
                pct = min(current_days / avg_up_days * 100, 100)
                reason = (
                    f"涨一段中期：当前已涨 {current_gain:.1f}%，持续 {current_days} 天，"
                    f"历史平均涨段涨 {avg_up:.1f}%/{avg_up_days} 天。"
                    f"目前进度约 {pct:.0f}%，涨了一段但还没走完"
                )
                score = 0.6
            elif avg_up_days > 0:
                phase = "rising_late"
                pct = min(current_days / avg_up_days * 100, 100)
                reason = (
                    f"涨一段晚期！当前已涨 {current_gain:.1f}%，持续 {current_days} 天，"
                    f"历史平均涨段涨 {avg_up:.1f}%/{avg_up_days} 天。"
                    f"目前进度约 {pct:.0f}%，涨得差不多了。"
                    f"涨完就该跌了，涨一段跌一段，这是规律"
                )
                score = min(1.0, current_days / avg_up_days)
            else:
                phase = "rising_mid"
                reason = f"上涨趋势：当前涨 {current_gain:.1f}%/{current_days} 天"
                score = 0.5

        elif current_trend == "down":
            if avg_down_days > 0 and current_days / avg_down_days < 0.4:
                phase = "falling_early"
                pct = min(current_days / avg_down_days * 100, 100)
                reason = (
                    f"跌一段早期：当前已跌 {abs(current_gain):.1f}%，持续 {current_days} 天，"
                    f"历史平均跌段跌 {avg_down:.1f}%/{avg_down_days} 天。"
                    f"目前进度约 {pct:.0f}%，刚开跌"
                )
                score = min(current_days / avg_down_days, 1.0) * 0.8
            elif avg_down_days > 0 and current_days / avg_down_days < 0.75:
                phase = "falling_mid"
                pct = min(current_days / avg_down_days * 100, 100)
                reason = (
                    f"跌一段中期：当前已跌 {abs(current_gain):.1f}%，持续 {current_days} 天，"
                    f"历史平均跌段跌 {avg_down:.1f}%/{avg_down_days} 天。"
                    f"目前进度约 {pct:.0f}%，跌了一段但还没跌透"
                )
                score = 0.5
            elif avg_down_days > 0:
                phase = "falling_late"
                pct = min(current_days / avg_down_days * 100, 100)
                reason = (
                    f"跌一段晚期！当前已跌 {abs(current_gain):.1f}%，持续 {current_days} 天，"
                    f"历史平均跌段跌 {avg_down:.1f}%/{avg_down_days} 天。"
                    f"目前进度约 {pct:.0f}%，跌得差不多了。"
                    f"跌透就该弹了，涨一段跌一段，这是规律"
                )
                score = min(1.0, current_days / avg_down_days)
            else:
                phase = "falling_mid"
                reason = f"下跌趋势：当前跌 {abs(current_gain):.1f}%/{current_days} 天"
                score = 0.5
        else:
            phase = "consolidating"
            reason = "横盘震荡状态，涨跌不明显。横盘久了就要变盘，得看方向"
            score = 0.3

        return RhythmResult(
            phase=phase,
            score=round(score, 2),
            reason=reason,
            details={
                "swings": swings,
                "current_trend": current_trend,
                "current_gain": round(current_gain, 2),
                "current_days": current_days,
                "avg_up": round(avg_up, 2),
                "avg_down": round(avg_down, 2),
                "avg_up_days": avg_up_days,
                "avg_down_days": avg_down_days,
            },
        )

    def _find_swing_points(self, close: pd.Series, window: int = 5) -> list[dict]:
        """Find swing high/low points.

        Args:
            close: Close price series
            window: Lookback window for local extremum detection

        Returns:
            List of {index, price, type} dicts
        """
        swings = []
        for i in range(window, len(close) - window):
            window_before = close.iloc[i - window: i]
            window_after = close.iloc[i + 1: i + window + 1]

            if len(window_before) < window or len(window_after) < window:
                continue

            if close.iloc[i] > window_before.max() and close.iloc[i] > window_after.max():
                swings.append({"index": i, "price": close.iloc[i], "type": "high"})
            elif close.iloc[i] < window_before.min() and close.iloc[i] < window_after.min():
                swings.append({"index": i, "price": close.iloc[i], "type": "low"})

        return swings

    def _analyze_current_trend(
        self, close: pd.Series, swings: list[dict]
    ) -> tuple[str, float, int]:
        """Analyze the current trend from the last swing point.

        Returns:
            (direction, pct_change, days_elapsed)
            direction: "up", "down", "flat"
        """
        if not swings:
            return "flat", 0.0, 0

        last_swing = swings[-1]
        last_idx = last_swing["index"]
        last_price = last_swing["price"]
        current_price = close.iloc[-1]

        gain = (current_price / last_price - 1) * 100
        days = len(close) - 1 - last_idx

        if abs(gain) < 0.5:
            return "flat", gain, days
        elif gain > 0:
            return "up", gain, days
        else:
            return "down", gain, days

    def _segment_stats(
        self, swings: list[dict]
    ) -> tuple[float, float, int, int]:
        """Calculate average up/down magnitude and duration.

        Returns:
            (avg_up_pct, avg_down_pct, avg_up_days, avg_down_days)
        """
        up_gains = []
        down_gains = []
        up_days = []
        down_days = []

        for i in range(1, len(swings)):
            prev = swings[i - 1]
            curr = swings[i]

            if prev["type"] == "low" and curr["type"] == "high":
                gain = (curr["price"] / prev["price"] - 1) * 100
                days = curr["index"] - prev["index"]
                up_gains.append(gain)
                up_days.append(days)
            elif prev["type"] == "high" and curr["type"] == "low":
                loss = (curr["price"] / prev["price"] - 1) * 100
                days = curr["index"] - prev["index"]
                down_gains.append(loss)
                down_days.append(days)

        avg_up = float(np.mean(up_gains)) if up_gains else 0
        avg_down = float(np.mean(down_gains)) if down_gains else 0
        avg_up_days = int(np.mean(up_days)) if up_days else 0
        avg_down_days = int(np.mean(down_days)) if down_days else 0

        return avg_up, avg_down, avg_up_days, avg_down_days
