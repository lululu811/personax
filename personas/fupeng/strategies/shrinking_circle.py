"""缩圈抱团检测策略 (Shrinking Circle Detection).

付鹏市场结构分析模型：
  风险偏好下降 → 资金从边缘向核心收敛（缩圈）
  缩圈路径：微盘 → 小盘 → 中盘 → 大盘核心

原理：
  通过对比不同市值指数的相对强弱，判断资金是否在收缩抱团。
  当大盘股显著跑赢小盘股、且红利/债券类资产走强时，
  说明市场处于缩圈状态。

信号判定：
  1. 沪深 300 近 20 日涨幅 > 中证 1000（大盘强于小盘）
  2. 红利指数近 20 日跑赢成长指数
  3. 涨停家数 / 上涨家数集中度偏高
  4. 近 5 日上涨家数占比 < 50%（广度差）

Usage:
    from personas.fupeng.strategies import ShrinkingCircleStrategy
    strategy = ShrinkingCircleStrategy()
    # Requires market-wide data, not single stock
    signal = strategy.detect_from_market(breadth_data, index_data)
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class ShrinkingCircleResult:
    """Result of shrinking circle detection."""
    phase: str           # "expanding", "stable", "shrinking", "final_circle"
    score: float         # 0.0-1.0, higher = more shrunk
    reason: str
    details: dict


class ShrinkingCircleStrategy:
    """付鹏缩圈抱团检测策略。

    判断市场是否处于资金收缩抱团状态。
    需要市场广度数据（非个股数据）。
    """

    name = "shrinking_circle"

    def detect(
        self,
        df: pd.DataFrame,
        large_cap_df: Optional[pd.DataFrame] = None,
        small_cap_df: Optional[pd.DataFrame] = None,
    ) -> ShrinkingCircleResult:
        """Detect shrinking circle from single stock context.

        For a single stock, we check if it's in the "core" group
        (large-cap, dividend-heavy, low-volatility) vs "periphery".

        Args:
            df: DataFrame with OHLCV data for a single stock
            large_cap_df: Optional large-cap index data
            small_cap_df: Optional small-cap index data

        Returns:
            ShrinkingCircleResult
        """
        close = df["close"]
        vol = df["vol"]

        # ---- Condition 1: Low volatility stock (抱团特征) ----
        returns = close.pct_change().dropna()
        vol_10 = returns.rolling(10).std().iloc[-1] * 100
        vol_60 = returns.rolling(60).std().iloc[-1] * 100
        vol_declining = vol_10 < vol_60 * 0.8

        # ---- Condition 2: Steady upward trend (抱团溢价) ----
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        above_trend = close.iloc[-1] > ma5 > ma20

        # ---- Condition 3: Volume pattern (缩量抱团) ----
        vol_5_avg = vol.iloc[-5:].mean()
        vol_20_avg = vol.iloc[-20:].mean()
        vol_shrinking = vol_5_avg < vol_20_avg * 0.8

        # ---- Condition 4: Concentrated gains (涨速集中) ----
        gain_5d = (close.iloc[-1] / close.iloc[-min(5, len(close))] - 1) * 100
        gain_20d = (close.iloc[-1] / close.iloc[-min(20, len(close))] - 1) * 100
        concentrated = gain_5d > gain_20d * 0.5  # Most gains in last 5 days

        # ---- Scoring ----
        conditions = [vol_declining, above_trend, vol_shrinking, concentrated]
        score = sum(conditions) / len(conditions)

        if score >= 0.75:
            phase = "final_circle"
            reason = (
                f"决赛圈抱团状态！10 日波动率 {vol_10:.2f}%（低于 60 日均值 {vol_60:.2f}%），"
                f"缩量抱团（5 日均量/20 日均量 = {vol_5_avg/vol_20_avg:.2f}），"
                f"股价稳居高位（> MA5 > MA20），近 5 日涨幅 {gain_5d:.1f}% 占 20 日涨幅 {gain_20d:.1f}% 的大部分。"
                f"决赛圈抱团 = 高度脆弱，警惕爆金币"
            )
        elif score >= 0.5:
            phase = "shrinking"
            reason = (
                f"缩圈进行中：波动率下降 {vol_10:.2f}% vs {vol_60:.2f}%，"
                f"量能萎缩，趋势向上。资金在向这类票收缩"
            )
        else:
            phase = "stable"
            reason = (
                f"非抱团状态：波动率 {vol_10:.2f}%，量能正常，"
                f"趋势未形成抱团特征。这只票不在核心抱团圈"
            )

        return ShrinkingCircleResult(
            phase=phase,
            score=score,
            reason=reason,
            details={
                "vol_10d_pct": round(vol_10, 2),
                "vol_60d_pct": round(vol_60, 2),
                "vol_declining": vol_declining,
                "above_trend": above_trend,
                "vol_shrinking": vol_shrinking,
                "concentrated": concentrated,
                "gain_5d": round(gain_5d, 2),
                "gain_20d": round(gain_20d, 2),
            },
        )

    def detect_from_market(
        self,
        breadth_data: dict,
        index_data: Optional[dict] = None,
    ) -> ShrinkingCircleResult:
        """Detect shrinking circle from market-wide breadth data.

        Args:
            breadth_data: dict with keys:
                - advance_count: number of advancing stocks
                - total_count: total stocks traded
                - limit_up_count: number of limit-up stocks
                - recent_5d_advance_ratio: advancing ratio avg over 5 days
            index_data: Optional dict with index performance:
                - hs300_20d: CSI 300 20-day return (%)
                - zq1000_20d: CSI 1000 20-day return (%)
                - dividend_20d: Dividend index 20-day return (%)
                - growth_20d: Growth index 20-day return (%)

        Returns:
            ShrinkingCircleResult
        """
        adv_ratio = breadth_data.get("advance_count", 0) / max(
            breadth_data.get("total_count", 1), 1
        )
        recent_ratio = breadth_data.get("recent_5d_advance_ratio", adv_ratio)
        breadth_poor = adv_ratio < 0.5
        breadth_worsening = recent_ratio < 0.5

        limit_ratio = breadth_data.get("limit_up_count", 0) / max(
            breadth_data.get("advance_count", 1), 1
        )
        concentration = limit_ratio > 0.1  # Top stocks dominate

        large_stronger = False
        dividend_stronger = False

        if index_data:
            hs = index_data.get("hs300_20d", 0)
            zq = index_data.get("zq1000_20d", 0)
            div = index_data.get("dividend_20d", 0)
            growth = index_data.get("growth_20d", 0)
            large_stronger = hs > zq
            dividend_stronger = div > growth

        conditions = [breadth_poor, breadth_worsening, concentration,
                      large_stronger, dividend_stronger]
        score = sum(conditions) / len(conditions)

        if score >= 0.8:
            phase = "final_circle"
            reason = "市场深度极差 + 大盘强于小盘 + 红利强于成长 = 决赛圈抱团"
        elif score >= 0.6:
            phase = "shrinking"
            reason = "缩圈进行中：广度收窄，资金向大盘/红利收缩"
        elif score >= 0.4:
            phase = "stable"
            reason = "市场结构基本稳定，无明显缩圈特征"
        else:
            phase = "expanding"
            reason = "扩圈状态：资金从核心向边缘扩散，风险偏好上升"

        return ShrinkingCircleResult(
            phase=phase,
            score=score,
            reason=reason,
            details={
                "advance_ratio": round(adv_ratio, 2),
                "recent_advance_ratio": round(recent_ratio, 2),
                "limit_concentration": round(limit_ratio, 2),
                "large_stronger": large_stronger,
                "dividend_stronger": dividend_stronger,
            },
        )
