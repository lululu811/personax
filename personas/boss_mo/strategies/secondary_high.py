"""次高与分水岭识别 (Secondary High & Watershed).

BOSS墨核心模型：
  次高是高位套顶的解套时机，不管未来往上还是往下，都不配在最高点持有

原理：
  通过识别前高、次高、分水岭、右脚四个关键价位，
  构建完整的交易地图，帮助用户理解当前价格在关键结构中的位置。

关键价位定义：
  - 前高：近期的最高价格
  - 次高：前高后反弹形成的局部高点（BOSS墨的核心做空位）
  - 分水岭：近期密集成交/横盘的核心价位带（多空分界线）
  - 右脚：回调后的低点（做多买入区）

策略判定：
  1. 扫描前 60 日的高低点，识别前高和次高
  2. 识别最近的横盘区域（分水岭）
  3. 识别回调低点（右脚）
  4. 输出关键价位地图和当前价格的相对位置
  5. 如果价格接近次高 → 提示做空机会
  6. 如果价格接近右脚 → 提示做多机会

Usage:
    from personas.boss_mo.strategies import SecondaryHighStrategy
    strategy = SecondaryHighStrategy()
    result = strategy.detect(df)
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class SecondaryHighResult:
    """Result of secondary high detection."""
    signal: str        # "near_secondary_high", "near_support", "near_watershed", "in_between", "at_all_time_high"
    score: float       # 0.0-1.0, confidence
    reason: str
    details: dict


class SecondaryHighStrategy:
    """BOSS墨次高与分水岭识别。

    构建关键价位地图，判断当前价格与关键结构的关系。
    """

    name = "secondary_high"

    def detect(self, df: pd.DataFrame) -> SecondaryHighResult:
        """Detect key price levels and current price position.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            SecondaryHighResult with signal classification
        """
        close = df["close"]
        high = df.get("high", close * 1.01)
        low = df.get("low", close * 0.99)
        current_price = close.iloc[-1]

        # ---- Identify key levels ----
        all_time_high = self._find_all_time_high(high)
        secondary_high = self._find_secondary_high(high, close)
        watershed = self._find_watershed(close)
        right_foot = self._find_right_foot(low, close)

        # ---- Current price position analysis ----
        distance_map = {}
        if secondary_high:
            dist_pct = (secondary_high["price"] - current_price) / current_price * 100
            distance_map["secondary_high"] = dist_pct
        if right_foot:
            dist_pct = (current_price - right_foot["price"]) / current_price * 100
            distance_map["right_foot"] = dist_pct
        if watershed:
            dist_pct = abs(current_price - watershed["price"]) / current_price * 100
            distance_map["watershed"] = dist_pct

        # ---- Signal determination ----
        threshold = 2.0  # Within 2% of a key level

        if secondary_high and distance_map.get("secondary_high", 999) <= threshold:
            signal = "near_secondary_high"
            reason = (
                f"价格接近次高 {secondary_high['price']:.2f}（距离 {distance_map['secondary_high']:.1f}%）。"
                f"次高是高位套顶的解套时机，不管未来往上还是往下，都不配在最高点持有。"
                f"这是做空的关键位置"
            )
            score = max(0.0, 1.0 - distance_map["secondary_high"] / threshold)

        elif right_foot and distance_map.get("right_foot", 999) <= threshold:
            signal = "near_support"
            reason = (
                f"价格接近右脚 {right_foot['price']:.2f}（距离 {distance_map['right_foot']:.1f}%）。"
                f"右脚是回调后的买入区域，有明确的止损位"
            )
            score = max(0.0, 1.0 - distance_map["right_foot"] / threshold)

        elif watershed and distance_map.get("watershed", 999) <= threshold:
            signal = "near_watershed"
            reason = (
                f"价格接近分水岭 {watershed['price']:.2f}（距离 {distance_map['watershed']:.1f}%）。"
                f"分水岭是多空分界线，突破后趋势可能改变，注意方向"
            )
            score = max(0.0, 1.0 - distance_map["watershed"] / threshold)

        elif not secondary_high and not right_foot:
            signal = "at_all_time_high"
            reason = (
                f"当前价格 {current_price:.2f} 接近前高 {all_time_high['price']:.2f}。"
                f"没有次高和右脚作为参考，说明趋势很强，但也意味着没有明确的止损位。"
                f"等它走出次高或右脚再说"
            )
            score = 0.3

        else:
            signal = "in_between"
            reason = (
                f"价格在关键价位之间：当前 {current_price:.2f}，"
                f"次高 {secondary_high['price'] if secondary_high else 'N/A'}，"
                f"右脚 {right_foot['price'] if right_foot else 'N/A'}，"
                f"分水岭 {watershed['price'] if watershed else 'N/A'}。"
                f"不在关键位置，学会空仓等机会"
            )
            score = 0.2

        return SecondaryHighResult(
            signal=signal,
            score=round(score, 2),
            reason=reason,
            details={
                "current_price": round(current_price, 2),
                "all_time_high": {
                    "price": all_time_high["price"],
                    "index": all_time_high["index"],
                } if all_time_high else None,
                "secondary_high": {
                    "price": secondary_high["price"],
                    "index": secondary_high["index"],
                    "distance_pct": round(distance_map.get("secondary_high", -1), 2),
                } if secondary_high else None,
                "watershed": {
                    "price": watershed["price"],
                    "index": watershed["index"],
                    "distance_pct": round(distance_map.get("watershed", -1), 2),
                } if watershed else None,
                "right_foot": {
                    "price": right_foot["price"],
                    "index": right_foot["index"],
                    "distance_pct": round(distance_map.get("right_foot", -1), 2),
                } if right_foot else None,
            },
        )

    def _find_all_time_high(self, high: pd.Series, lookback: int = 120) -> dict:
        """Find the all-time high within the lookback window."""
        recent = high.iloc[-lookback:]
        max_price = recent.max()
        return {"price": max_price, "index": int(recent.idxmax())}

    def _find_secondary_high(self, high: pd.Series, close: pd.Series, lookback: int = 120) -> Optional[dict]:
        """Find the secondary high after the all-time high.

        次高定义：前高后反弹形成的局部高点（通常低于前高）
        """
        recent_high = high.iloc[-lookback:]
        max_price = recent_high.max()
        max_idx = int(recent_high.idxmax())

        # Search for local maxima after the ATH
        post_high = high.iloc[max_idx - recent_high.index[0] + 1:]
        if len(post_high) < 10:
            return None

        for i in range(5, len(post_high) - 5):
            window = post_high.iloc[i - 5: i + 6]
            if (post_high.iloc[i] == window.max()
                    and post_high.iloc[i] < max_price
                    and post_high.iloc[i] > max_price * 0.95):
                return {
                    "price": post_high.iloc[i],
                    "index": int(post_high.index[i]),
                }

        return None

    def _find_watershed(self, close: pd.Series, lookback: int = 60) -> Optional[dict]:
        """Find the watershed (consolidation zone).

        分水岭定义：近期密集成交/横盘的核心价位带
        """
        recent = close.iloc[-lookback:]
        returns = recent.pct_change().dropna()

        # Check if there's a consolidation zone (low volatility segment)
        for start in range(0, len(returns) - 15, 5):
            segment = returns.iloc[start: start + 15]
            vol = segment.std()
            if vol < 0.008:  # Low volatility = consolidation
                avg_price = close.iloc[recent.index[start]: recent.index[start + 15]].mean()
                return {
                    "price": avg_price,
                    "index": int(recent.index[start]),
                }

        # Fallback: use the median price of recent range
        return {
            "price": recent.median(),
            "index": int(recent.index[len(recent) // 2]),
        }

    def _find_right_foot(self, low: pd.Series, close: pd.Series, lookback: int = 120) -> Optional[dict]:
        """Find the right foot (higher low after the main low).

        右脚定义：回调后的低点（做多买入区）
        """
        recent_low = low.iloc[-lookback:]
        min_price = recent_low.min()
        min_idx = int(recent_low.idxmin())

        # Search for local minima after the main low
        post_low = low.iloc[min_idx - recent_low.index[0] + 1:]
        if len(post_low) < 10:
            return None

        for i in range(5, len(post_low) - 5):
            window = post_low.iloc[i - 5: i + 6]
            if (post_low.iloc[i] == window.min()
                    and post_low.iloc[i] > min_price
                    and post_low.iloc[i] < min_price * 1.05):
                return {
                    "price": post_low.iloc[i],
                    "index": int(post_low.index[i]),
                }

        return None
