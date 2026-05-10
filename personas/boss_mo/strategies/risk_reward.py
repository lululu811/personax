"""盈亏比计算策略 (Risk-Reward Calculator).

BOSS墨核心模型：
  点位 > 方向，方向可以错，盈亏比长期稳定就必定赚钱

原理：
  在入场前自动计算做多和做空两种方向的盈亏比，
  基于最近的支撑位和阻力位，给出明确的交易建议。

策略判定：
  1. 自动识别最近的支撑位（前低/右脚）和阻力位（前高/次高）
  2. 计算做多盈亏比 = (阻力位 - 当前价) / (当前价 - 支撑位)
  3. 计算做空盈亏比 = (当前价 - 支撑位) / (阻力位 - 当前价)
  4. 输出：哪个方向盈亏比划算（≥2:1），或都不划算则建议空仓

关键价位识别：
  - 次高：高点后反弹形成的局部高点（BOSS墨的核心做空位）
  - 分水岭：近期横盘/震荡的核心价位带（多空分界线）
  - 右脚：回调后的低点区域（做多买入区）

Usage:
    from personas.boss_mo.strategies import RiskRewardStrategy
    strategy = RiskRewardStrategy()
    result = strategy.detect(df)
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class RiskRewardResult:
    """Result of risk-reward calculation."""
    recommendation: str    # "long", "short", "wait", "no_trade"
    long_ratio: float      # 做多盈亏比 (目标利润 / 止损风险)
    short_ratio: float     # 做空盈亏比
    reason: str
    details: dict


class RiskRewardStrategy:
    """BOSS墨盈亏比计算策略。

    基于关键价位自动计算多空两种方向的盈亏比。
    """

    name = "risk_reward"

    def detect(self, df: pd.DataFrame) -> RiskRewardResult:
        """Calculate risk-reward ratio for both long and short directions.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            RiskRewardResult with recommendation
        """
        close = df["close"]
        high = df.get("high", close)
        low = df.get("low", close)

        current_price = close.iloc[-1]

        # ---- Identify key price levels ----
        resistance = self._find_resistance(high, close)  # 前高/次高
        support = self._find_support(low, close)         # 前低/右脚

        # ---- Calculate long risk-reward ----
        if support and resistance:
            long_target = resistance["price"] - current_price
            long_risk = current_price - support["price"]
            long_ratio = long_target / long_risk if long_risk > 0 else 0

            short_target = current_price - support["price"]
            short_risk = resistance["price"] - current_price
            short_ratio = short_target / short_risk if short_risk > 0 else 0
        else:
            long_ratio = 0
            short_ratio = 0

        # ---- Decision ----
        min_ratio = 2.0  # BOSS墨的标准：盈亏比 2:1 以下不做

        if long_ratio >= min_ratio and long_ratio > short_ratio:
            recommendation = "long"
            reason = (
                f"做多盈亏比划算！目标 {resistance['price']:.2f}（{resistance['type']}），"
                f"止损 {support['price']:.2f}（{support['type']}），"
                f"盈亏比 {long_ratio:.1f}:1。"
                f"方向可以错，点位好就行——这就叫盈亏比"
            )
        elif short_ratio >= min_ratio and short_ratio > long_ratio:
            recommendation = "short"
            reason = (
                f"做空盈亏比划算！目标 {support['price']:.2f}（{support['type']}），"
                f"止损 {resistance['price']:.2f}（{resistance['type']}），"
                f"盈亏比 {short_ratio:.1f}:1。"
                f"方向可以错，点位好就行"
            )
        elif long_ratio > 0 and short_ratio > 0:
            # Both exist but neither meets 2:1 threshold
            recommendation = "wait"
            reason = (
                f"做多盈亏比 {long_ratio:.1f}:1，做空盈亏比 {short_ratio:.1f}:1，"
                f"都不够 2:1。盈亏比不划算就不做——宁可错过，也不乱做。"
                f"学会空仓也是本事"
            )
        else:
            recommendation = "no_trade"
            reason = (
                f"关键价位不清晰（支撑: {support}, 阻力: {resistance}）。"
                f"看不清楚的时候最好是不做，等它走出来再说"
            )

        return RiskRewardResult(
            recommendation=recommendation,
            long_ratio=round(long_ratio, 2),
            short_ratio=round(short_ratio, 2),
            reason=reason,
            details={
                "current_price": round(current_price, 2),
                "resistance": resistance,
                "support": support,
                "min_ratio": min_ratio,
            },
        )

    def _find_resistance(
        self, high: pd.Series, close: pd.Series, lookback: int = 60
    ) -> Optional[dict]:
        """Find nearest resistance level (前高/次高).

        Returns:
            {"price": float, "type": str} or None
        """
        recent = high.iloc[-lookback:]

        # Find the highest point
        max_price = recent.max()
        max_idx = recent.idxmax()

        # Check if current price is near the high (if so, resistance is close)
        # Look for a "次高" (second high) after the main high
        post_high = high.iloc[max_idx - recent.index[0]:]
        if len(post_high) > 10:
            # Find local maxima after the main high
            for i in range(5, len(post_high) - 5):
                window = post_high.iloc[i - 5: i + 6]
                if post_high.iloc[i] == window.max() and post_high.iloc[i] < max_price * 1.01:
                    return {
                        "price": post_high.iloc[i],
                        "type": "次高",
                        "index": int(post_high.index[i]),
                    }

        return {
            "price": max_price,
            "type": "前高",
            "index": int(max_idx),
        }

    def _find_support(
        self, low: pd.Series, close: pd.Series, lookback: int = 60
    ) -> Optional[dict]:
        """Find nearest support level (前低/右脚).

        Returns:
            {"price": float, "type": str} or None
        """
        recent = low.iloc[-lookback:]

        # Find the lowest point
        min_price = recent.min()
        min_idx = recent.idxmin()

        # Look for a "右脚" (higher low after the main low)
        post_low = low.iloc[min_idx - recent.index[0]:]
        if len(post_low) > 10:
            # Find local minima after the main low
            for i in range(5, len(post_low) - 5):
                window = post_low.iloc[i - 5: i + 6]
                if post_low.iloc[i] == window.min() and post_low.iloc[i] > min_price * 0.99:
                    return {
                        "price": post_low.iloc[i],
                        "type": "右脚",
                        "index": int(post_low.index[i]),
                    }

        return {
            "price": min_price,
            "type": "前低",
            "index": int(min_idx),
        }
