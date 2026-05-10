"""哑铃策略信号 (Dumbbell Strategy Signal).

付鹏哑铃配置模型：
  一头是保险（确定性/红利/低风偏），一头是彩票（成长/AI/高风偏）
  中间没有打折品——不碰中间地带

原理：
  在风险偏好收缩、总量缺乏机会的环境下，最优配置是哑铃结构：
  - 低风偏端：高股息、现金流稳定、类现金资产（银行、电力、国债）
  - 高风偏端：高弹性、政策兜底、远期预期（AI、科技、小盘成长）
  - 中间地带（传统周期、消费蓝筹）最危险——既没确定性也没弹性

信号判定（个股维度）：
  1. 高股息率 > 4% + 低波动 → 低风偏端（确定性）
  2. 高成长预期 + 高波动 → 高风偏端（弹性）
  3. 两者都不是 → 中间地带（回避）

Usage:
    from personas.fupeng.strategies import DumbbellStrategy
    strategy = DumbbellStrategy()
    signal = strategy.detect(df)
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from tools.quant.technical import atr


@dataclass
class DumbbellResult:
    """Result of dumbbell signal detection."""
    position: str        # "defensive", "offensive", "middle"
    score: float         # 0.0-1.0, how well it fits dumbbell ends
    reason: str
    details: dict


class DumbbellStrategy:
    """付鹏哑铃策略信号。

    判断个股位于哑铃的哪一端，或是否在危险的中间地带。
    """

    name = "dumbbell"

    def detect(
        self,
        df: pd.DataFrame,
        dividend_yield: Optional[float] = None,
        pe_ratio: Optional[float] = None,
    ) -> DumbbellResult:
        """Detect which end of the dumbbell this stock sits on.

        Args:
            df: DataFrame with OHLCV data
            dividend_yield: Optional dividend yield (%)
            pe_ratio: Optional PE ratio

        Returns:
            DumbbellResult with position classification
        """
        close = df["close"]
        vol = df["vol"]

        # ---- Volatility (风偏判断) ----
        returns = close.pct_change().dropna()
        vol_20 = returns.rolling(20).std().iloc[-1] * 100
        atr_result = atr.compute(df)
        atr_pct = atr_result.data["atr"].iloc[-1] / close.iloc[-1] * 100

        # ---- Trend (趋势判断) ----
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        trend_up = close.iloc[-1] > ma20 > ma60

        # ---- Volume pattern ----
        vol_5_avg = vol.iloc[-5:].mean()
        vol_20_avg = vol.iloc[-20:].mean()
        vol_ratio = vol_5_avg / vol_20_avg if vol_20_avg > 0 else 1.0

        # ---- Growth proxy (成长性代理：短期动量) ----
        gain_10d = (close.iloc[-1] / close.iloc[-min(10, len(close))] - 1) * 100
        gain_60d = (close.iloc[-1] / close.iloc[-min(60, len(close))] - 1) * 100
        momentum = gain_10d > 5 and gain_60d > 15

        # ---- Defensive scoring ----
        defensive_score = 0
        if dividend_yield is not None:
            if dividend_yield >= 4:
                defensive_score += 2
            elif dividend_yield >= 2:
                defensive_score += 1
        if vol_20 < 1.5:
            defensive_score += 2
        elif vol_20 < 2.5:
            defensive_score += 1
        if atr_pct < 2:
            defensive_score += 1

        # ---- Offensive scoring ----
        offensive_score = 0
        if momentum:
            offensive_score += 2
        if vol_20 > 3:
            offensive_score += 2
        elif vol_20 > 2:
            offensive_score += 1
        if atr_pct > 4:
            offensive_score += 1
        if vol_ratio > 1.5:
            offensive_score += 1

        # ---- Classification ----
        diff = abs(defensive_score - offensive_score)
        if defensive_score >= 4 and diff >= 2:
            position = "defensive"
            reason = (
                f"哑铃防御端：股息率 {dividend_yield}%，20 日波动率 {vol_20:.1f}%，"
                f"ATR 占比 {atr_pct:.1f}%。属于类现金/确定性资产。"
                f"付鹏原话：'一头是保险'——这是哑铃的保险端"
            )
            score = min(defensive_score / 6, 1.0)
        elif offensive_score >= 4 and diff >= 2:
            position = "offensive"
            reason = (
                f"哑铃进攻端：10 日涨幅 {gain_10d:.1f}%，60 日涨幅 {gain_60d:.1f}%，"
                f"20 日波动率 {vol_20:.1f}%，量比 {vol_ratio:.1f}x。"
                f"属于高弹性/高预期资产。付鹏原话：'一头是彩票'——这是哑铃的彩票端"
            )
            score = min(offensive_score / 6, 1.0)
        else:
            position = "middle"
            reason = (
                f"中间地带（回避）：波动率 {vol_20:.1f}%，"
                f"10 日涨幅 {gain_10d:.1f}%。"
                f"既没有确定性的现金流支撑，也没有高弹性的远期预期。"
                f"付鹏原话：'中间没有打折品'——这种票最危险"
            )
            score = 0.0

        return DumbbellResult(
            position=position,
            score=round(score, 2),
            reason=reason,
            details={
                "defensive_score": defensive_score,
                "offensive_score": offensive_score,
                "vol_20d_pct": round(vol_20, 2),
                "atr_pct": round(atr_pct, 2),
                "gain_10d": round(gain_10d, 2),
                "gain_60d": round(gain_60d, 2),
                "vol_ratio": round(vol_ratio, 2),
                "trend_up": trend_up,
                "momentum": momentum,
                "dividend_yield": dividend_yield,
            },
        )
