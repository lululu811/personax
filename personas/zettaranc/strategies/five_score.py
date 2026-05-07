"""Five Score Strategy - Zettaranc's position holding checklist.

少妇战法V1.3 - Daily holding score for preventing premature selling.
5-point checklist, each criterion met = 1 point.

Scoring:
1. Close rising (1pt if close > prev_close)
2. Above BBI (1pt if close > BBI)
3. No huge bearish candle (1pt if not巨量阴线)
4. Trend up (1pt if N-structure intact)
5. KDJ not dead cross (1pt if J > D)

Score interpretation:
- 5 = hold firmly
- 4 = hold
- 3 = halve position
- <= 2 = exit

Usage:
    from personas.zettaranc.strategies import FiveScoreStrategy

    strategy = FiveScoreStrategy()
    signal = strategy.score(df)
    print(f"Score: {signal.score}/5, Action: {signal.action}")
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import kdj, bbi


@dataclass
class StrategySignal:
    """Result of a strategy detection."""
    action: str
    confidence: float
    reason: str
    metadata: dict


@dataclass
class FiveScoreResult:
    """Result of five-point scoring."""
    score: int           # Total score (0-5)
    criteria: dict       # Each criterion result
    action: str          # "hold_firm", "hold", "halve", "exit"
    confidence: float


class FiveScoreStrategy:
    """Five-point scoring for position management.

    From Z哥's 少妇战法V1.3 - prevents selling too early.
    """

    name = "five_score"

    def score(self, df: pd.DataFrame) -> FiveScoreResult:
        """Calculate five-point score.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            FiveScoreResult with score, individual criteria, and recommended action
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["vol"]

        criteria = {}

        # 1. Close rising (1pt if close > prev_close)
        close_rising = close > close.shift(1)
        criteria["close_rising"] = {
            "met": close_rising.iloc[-1],
            "description": "收盘价上升",
        }

        # 2. Above BBI (1pt if close > BBI)
        bbi_result = bbi.compute(df)
        bbi_val = bbi_result.data["bbi"]
        above_bbi = close > bbi_val
        criteria["above_bbi"] = {
            "met": above_bbi.iloc[-1],
            "description": "价格在BBI上方",
        }

        # 3. No huge bearish candle (1pt if not巨量阴线)
        body = close - open_
        is_bearish = body < 0
        avg_volume = volume.rolling(window=20).mean()
        is_huge_volume = volume > avg_volume * 2.5
        huge_bearish = is_bearish & is_huge_volume
        criteria["no_huge_bearish"] = {
            "met": not huge_bearish.iloc[-1],
            "description": "无巨量阴线",
        }

        # 4. Trend up (higher lows in recent 10 days)
        # Simplified: low is higher than low 10 days ago
        low_10d_ago = low.shift(10)
        trend_up = close > close.shift(5)  # Higher close than 5 days ago
        criteria["trend_up"] = {
            "met": trend_up.iloc[-1],
            "description": "趋势向上",
        }

        # 5. KDJ not dead cross (J > D)
        kdj_result = kdj.compute(df)
        j = kdj_result.data["J"]
        d = kdj_result.data["D"]
        j_above_d = j > d
        criteria["kdj_bullish"] = {
            "met": j_above_d.iloc[-1],
            "description": "KDJ多头(J>D)",
        }

        # Calculate total score
        total_score = sum(1 for c in criteria.values() if c["met"])

        # Determine action based on score
        if total_score >= 5:
            action = "hold_firm"
            confidence = 0.95
            action_desc = "坚定持有"
        elif total_score == 4:
            action = "hold"
            confidence = 0.8
            action_desc = "持有"
        elif total_score == 3:
            action = "halve"
            confidence = 0.6
            action_desc = "考虑减半仓"
        else:
            action = "exit"
            confidence = 0.85
            action_desc = "考虑退出"

        reason = f"{total_score}分({action_desc}): " + ", ".join(
            f"{'✓' if c['met'] else '✗'}{c['description']}"
            for c in criteria.values()
        )

        return FiveScoreResult(
            score=total_score,
            criteria=criteria,
            action=action,
            confidence=confidence,
        )

    def detect(self, df: pd.DataFrame) -> StrategySignal:
        """Alias for score() with StrategySignal return type."""
        result = self.score(df)
        return StrategySignal(
            action=result.action,
            confidence=result.confidence,
            reason=result.criteria,
            metadata={"score": result.score, "action": result.action},
        )
