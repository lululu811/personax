"""爆金币预警策略 (Explosive Gold Warning).

付鹏核心风险预警模型：
  确定性极高 + 波动率极低 + 杠杆过度堆积 = 闪崩前兆

原理：
  当一只股票（或板块）长时间稳定上涨、波动率持续压缩、
  成交量异常放大时，说明大量杠杆资金在确定性中过度堆积。
  一旦出现任何催化剂，去杠杆过程同样剧烈。

信号判定：
  1. 近 20 日涨幅 > 15%（确定性高）
  2. 近 5 日 ATR/均线 < 2%（波动率极低）
  3. 近 3 日平均量比 > 2（杠杆堆积）
  4. 价格在 5 日均线上方持续运行 > 7 天（单边行情）

Usage:
    from personas.fupeng.strategies import ExplosiveGoldStrategy
    strategy = ExplosiveGoldStrategy()
    signal = strategy.detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import atr


@dataclass
class ExplosiveGoldResult:
    """Result of explosive gold detection."""
    risk_level: str          # "high", "medium", "low"
    score: float             # 0.0 - 1.0, higher = more dangerous
    reason: str
    details: dict


class ExplosiveGoldStrategy:
    """付鹏爆金币预警策略。

    检测高确定性 + 低波动 + 杠杆堆积 = 闪崩风险。
    """

    name = "explosive_gold"

    def detect(self, df: pd.DataFrame) -> ExplosiveGoldResult:
        """Detect explosive gold warning signal.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            ExplosiveGoldResult with risk level and scoring
        """
        close = df["close"]
        vol = df["vol"]

        # ---- Condition 1: Recent gain (确定性) ----
        gain_20d = (close.iloc[-1] / close.iloc[-min(20, len(close))] - 1) * 100
        gain_10d = (close.iloc[-1] / close.iloc[-min(10, len(close))] - 1) * 100
        high_certainty = gain_20d > 15 or gain_10d > 8

        # ---- Condition 2: Low volatility (波动率压缩) ----
        atr_result = atr.compute(df)
        atr_values = atr_result.data["atr"]
        short_atr = atr_values.iloc[-5:].mean() / close.iloc[-5:].mean() * 100
        long_atr = atr_values.iloc[-20:].mean() / close.iloc[-20:].mean() * 100
        low_vol = short_atr < 2.0 and short_atr < long_atr * 0.7

        # ---- Condition 3: Volume surge (杠杆堆积) ----
        vol_avg_20 = vol.iloc[-20:].mean()
        vol_avg_3 = vol.iloc[-3:].mean()
        vol_ratio = vol_avg_3 / vol_avg_20 if vol_avg_20 > 0 else 1.0
        leverage_buildup = vol_ratio > 2.0

        # ---- Condition 4: Sticky above MA5 (单边行情) ----
        ma5 = close.rolling(5).mean()
        days_above_ma5 = (close.iloc[-10:] > ma5.iloc[-10:]).sum()
        sticky_run = days_above_ma5 >= 7

        # ---- Scoring ----
        conditions = [high_certainty, low_vol, leverage_buildup, sticky_run]
        score = sum(conditions) / len(conditions)

        if score >= 0.75:
            risk_level = "high"
            reason = (
                f"爆金币高风险预警！近 20 日涨幅 {gain_20d:.1f}%，"
                f"5 日波动率 {short_atr:.2f}%（低于长期均值 {long_atr:.2f}%），"
                f"近 3 日均量是 20 日均量的 {vol_ratio:.1f} 倍，"
                f"近 10 日有 {days_above_ma5} 天收盘价在 MA5 上方。"
                f"确定性极高 + 波动率极低 + 杠杆堆积 = 闪崩前兆"
            )
        elif score >= 0.5:
            risk_level = "medium"
            reason = (
                f"中等风险：涨幅 {gain_20d:.1f}%，波动率 {short_atr:.2f}%，"
                f"量比 {vol_ratio:.1f}x。部分条件满足，需持续监控"
            )
        else:
            risk_level = "low"
            reason = (
                f"低风险：涨幅 {gain_20d:.1f}%，波动率 {short_atr:.2f}%，"
                f"量比 {vol_ratio:.1f}x。暂未见爆金币信号"
            )

        return ExplosiveGoldResult(
            risk_level=risk_level,
            score=score,
            reason=reason,
            details={
                "gain_20d": round(gain_20d, 2),
                "gain_10d": round(gain_10d, 2),
                "short_atr_pct": round(short_atr, 2),
                "long_atr_pct": round(long_atr, 2),
                "vol_ratio": round(vol_ratio, 2),
                "days_above_ma5": int(days_above_ma5),
                "conditions": {
                    "high_certainty": high_certainty,
                    "low_volatility": low_vol,
                    "leverage_buildup": leverage_buildup,
                    "sticky_run": sticky_run,
                },
            },
        )
