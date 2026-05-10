"""B1 Strategy - Zettaranc's primary buy signal.

B1 (Buy Point 1) is Z哥's most important entry signal.
Concept: J value < 13 indicates oversold, potential bounce.

B1 Strategy:
1. J < 13 (general) or J < -10 (conservative/young-wife)
2. KDJ golden cross forms
3. White line above yellow line (trend confirmation)
4. Volume supports the move

Usage:
    from personas.zettaranc.strategies import B1Strategy

    strategy = B1Strategy()
    signal = strategy.detect(df)
    print(signal.action)  # "buy", "sell", "hold"
"""

import pandas as pd

from tools.quant.technical import kdj, bbi
from orchestration.models import StrategySignal


class B1Strategy:
    """B1 buy point strategy.

    Z哥's primary entry signal - oversold bounce with confirmation.
    """

    name = "b1"

    def detect(
        self,
        df: pd.DataFrame,
        conservative: bool = False,
        require_bbi_confirm: bool = True,
    ) -> StrategySignal:
        """Detect B1 buy signal.

        Args:
            df: DataFrame with OHLCV data
            conservative: If True, use J < -10 instead of J < 13
            require_bbi_confirm: If True, require price above BBI

        Returns:
            StrategySignal with action, confidence, and reasoning
        """
        # Get KDJ data
        kdj_result = kdj.compute(df)
        j = kdj_result.data["J"]
        k = kdj_result.data["K"]
        d = kdj_result.data["D"]
        kdj_signals = kdj_result.signals

        # Get BBI data
        bbi_result = bbi.compute(df)
        close = df["close"]
        above_bbi = close > bbi_result.data["bbi"]

        # Current values
        current_j = j.iloc[-1]
        current_k = k.iloc[-1]
        current_d = d.iloc[-1]

        # Check conditions
        conditions_met = []
        conditions_failed = []

        # Condition 1: J below threshold
        if conservative:
            b1_condition = current_j < -10
            j_threshold = -10
        else:
            b1_condition = current_j < 13
            j_threshold = 13

        if b1_condition:
            conditions_met.append(f"J={current_j:.1f}<{j_threshold}")
        else:
            conditions_failed.append(f"J={current_j:.1f} not < {j_threshold}")

        # Condition 2: Golden cross (K crosses above D)
        golden_cross = kdj_signals.get("golden_cross", False)
        if golden_cross:
            conditions_met.append("KDJ golden cross")
        else:
            conditions_failed.append("No KDJ golden cross")

        # Condition 3: K > D (current)
        k_above_d = current_k > current_d
        if k_above_d:
            conditions_met.append("K>D")
        else:
            conditions_failed.append("K not > D")

        # Condition 4: BBI confirmation
        current_above_bbi = above_bbi.iloc[-1]
        if require_bbi_confirm:
            if current_above_bbi:
                conditions_met.append("Above BBI")
            else:
                conditions_failed.append("Below BBI (required)")

        # Calculate confidence
        if len(conditions_met) >= 3:
            confidence = 0.8 + (len(conditions_met) - 3) * 0.1
            action = "buy"
            reason = f"B1信号: {', '.join(conditions_met)}"
        elif len(conditions_met) >= 2 and b1_condition:
            confidence = 0.6
            action = "hold"
            reason = f"B1酝酿中: {', '.join(conditions_met)}, 等待: {', '.join(conditions_failed)}"
        else:
            confidence = 0.0
            action = "hold"
            reason = f"无B1信号: {', '.join(conditions_failed)}"

        return StrategySignal(
            action=action,
            confidence=min(confidence, 1.0),
            reason=reason,
            metadata={
                "j_value": current_j,
                "k_value": current_k,
                "d_value": current_d,
                "conditions_met": conditions_met,
                "conditions_failed": conditions_failed,
                "conservative": conservative,
            },
        )
