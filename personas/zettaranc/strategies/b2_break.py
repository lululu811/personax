"""B2 Break Strategy - Zettaranc's confirmation signal after B1.

B2 (Breakout Point 2) is the confirmation signal that follows B1.
Concept: After B1, look for breakout confirmation with volume surge.

B2 Break Conditions:
1. B1 signal within last 5 days (J < 13)
2. Gain >= 4%
3. Volume > previous day * 1.2
4. KDJ J < 55
5. No long upper shadow (upper / body < 0.5)

Usage:
    from personas.zettaranc.strategies import B2BreakStrategy

    strategy = B2BreakStrategy()
    signal = strategy.detect(df)
"""

from dataclasses import dataclass
import pandas as pd

from tools.quant.technical import kdj


@dataclass
class StrategySignal:
    """Result of a strategy detection."""
    action: str
    confidence: float
    reason: str
    metadata: dict


class B2BreakStrategy:
    """B2 breakout confirmation strategy.

    Follows B1 - confirms the bounce has strength for continued rise.
    """

    name = "b2_break"

    def detect(
        self,
        df: pd.DataFrame,
        min_gain_pct: float = 4.0,
        volume_mult: float = 1.2,
        j_threshold: float = 55.0,
        shadow_ratio: float = 0.5,
    ) -> StrategySignal:
        """Detect B2 break signal.

        Args:
            df: DataFrame with OHLCV data
            min_gain_pct: Minimum gain percentage (default 4%)
            volume_mult: Volume must exceed previous day by this multiplier (default 1.2)
            j_threshold: J must be below this (default 55)
            shadow_ratio: Max upper shadow to body ratio (default 0.5)

        Returns:
            StrategySignal with action, confidence, and reasoning
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["vol"]

        # Get KDJ
        kdj_result = kdj.compute(df)
        j = kdj_result.data["J"]
        k = kdj_result.data["K"]
        d = kdj_result.data["D"]

        # Condition 1: B1 within last 5 days (J < 13)
        b1_signal = j < 13
        has_b1_recently = b1_signal.rolling(window=5).max().fillna(False)

        # Condition 2: Gain >= 4%
        gain_pct = (close - close.shift(1)) / close.shift(1) * 100
        big_gain = gain_pct >= min_gain_pct

        # Condition 3: Volume surge > 20%
        volume_surge = volume > volume.shift(1) * volume_mult

        # Condition 4: J < 55
        j_below_55 = j < j_threshold

        # Condition 5: No long upper shadow
        body = abs(close - open_)
        body = body.replace(0, 0.001)  # Avoid division by zero
        upper_shadow = high - close.where(close >= open_, open_)
        no_long_shadow = (upper_shadow / body) < shadow_ratio

        # Current day values
        current_gain = gain_pct.iloc[-1]
        current_volume_ratio = volume.iloc[-1] / volume.shift(1).iloc[-1] if volume.shift(1).iloc[-1] > 0 else 0
        current_j = j.iloc[-1]
        current_upper_shadow_ratio = (upper_shadow / body).iloc[-1]

        # Check conditions
        conditions_met = []
        conditions_failed = []

        if has_b1_recently.iloc[-1]:
            conditions_met.append("B1 in last 5 days")
        else:
            conditions_failed.append("No B1 recently")

        if big_gain.iloc[-1]:
            conditions_met.append(f"Gain {current_gain:.1f}%>={min_gain_pct}%")
        else:
            conditions_failed.append(f"Gain {current_gain:.1f}%<{min_gain_pct}%")

        if volume_surge.iloc[-1]:
            conditions_met.append(f"Volume {current_volume_ratio:.1f}x>previous")
        else:
            conditions_failed.append(f"Volume {current_volume_ratio:.1f}x<=previous")

        if j_below_55.iloc[-1]:
            conditions_met.append(f"J={current_j:.1f}<{j_threshold}")
        else:
            conditions_failed.append(f"J={current_j:.1f}>={j_threshold}")

        if no_long_shadow.iloc[-1]:
            conditions_met.append(f"Upper shadow ratio {current_upper_shadow_ratio:.2f}<{shadow_ratio}")
        else:
            conditions_failed.append(f"Long shadow ratio {current_upper_shadow_ratio:.2f}>={shadow_ratio}")

        # Determine action
        if len(conditions_met) >= 4:
            confidence = 0.85
            action = "buy"
            reason = f"B2确认: {', '.join(conditions_met)}"
        elif len(conditions_met) >= 3:
            confidence = 0.6
            action = "hold"
            reason = f"B2酝酿: {', '.join(conditions_met)}"
        else:
            confidence = 0.0
            action = "hold"
            reason = f"无B2: {', '.join(conditions_failed)}"

        return StrategySignal(
            action=action,
            confidence=min(confidence, 1.0),
            reason=reason,
            metadata={
                "gain_pct": current_gain,
                "volume_ratio": current_volume_ratio,
                "j_value": current_j,
                "upper_shadow_ratio": current_upper_shadow_ratio,
                "conditions_met": conditions_met,
                "conditions_failed": conditions_failed,
            },
        )
