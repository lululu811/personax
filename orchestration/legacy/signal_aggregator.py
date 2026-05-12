"""Signal Aggregator - Resolves conflicts when multiple personas give signals."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

import pandas as pd


class ConflictStrategy(Enum):
    """Strategy for resolving signal conflicts."""
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence scores
    ZETTARANC_FIRST = "zettaranc_first"          # Zettaranc has final say on quant
    CONSENSUS = "consensus"                      # All must agree
    MOST_BULLISH = "most_bullish"               # Take most bullish signal


@dataclass
class PersonaSignal:
    """A signal from a single persona."""
    persona: str
    action: str           # "buy", "sell", "hold", "warning"
    confidence: float     # 0.0 - 1.0
    reason: str          # Human-readable reason
    metadata: dict       # Additional context


@dataclass
class AggregatedSignal:
    """Result of aggregating signals from multiple personas."""
    action: str
    confidence: float
    reasons: list[str]    # All reasons from contributing personas
    conflict_detected: bool
    resolution_strategy: str
    persona_signals: list[PersonaSignal]


class SignalAggregator:
    """Aggregates signals from multiple personas and resolves conflicts.

    Usage:
        aggregator = SignalAggregator(strategy=ConflictStrategy.CONFIDENCE_WEIGHTED)
        result = aggregator.aggregate([
            PersonaSignal("zettaranc", "buy", 0.8, "B1+B2 confirmed"),
            PersonaSignal("munger", "hold", 0.6, "ROE below threshold"),
        ])
    """

    def __init__(self, strategy: ConflictStrategy = ConflictStrategy.CONFIDENCE_WEIGHTED):
        self.strategy = strategy

    def aggregate(self, signals: list[PersonaSignal]) -> AggregatedSignal:
        """Aggregate multiple persona signals into a single decision.

        Args:
            signals: List of signals from different personas

        Returns:
            AggregatedSignal with resolved action and reasoning
        """
        if not signals:
            return AggregatedSignal(
                action="hold",
                confidence=0.0,
                reasons=["No signals available"],
                conflict_detected=False,
                resolution_strategy="none",
                persona_signals=[],
            )

        # Check for conflicts
        actions = set(s.action for s in signals)
        conflict = len(actions) > 1
        strategies_used = []

        if self.strategy == ConflictStrategy.CONFIDENCE_WEIGHTED:
            final_action, confidence = self._confidence_weighted(signals)
            strategies_used.append("confidence_weighted")

        elif self.strategy == ConflictStrategy.ZETTARANC_FIRST:
            final_action, confidence = self._zettaranc_first(signals)
            strategies_used.append("zettaranc_first")

        elif self.strategy == ConflictStrategy.CONSENSUS:
            final_action, confidence = self._consensus(signals)
            strategies_used.append("consensus")

        elif self.strategy == ConflictStrategy.MOST_BULLISH:
            final_action, confidence = self._most_bullish(signals)
            strategies_used.append("most_bullish")

        return AggregatedSignal(
            action=final_action,
            confidence=confidence,
            reasons=[s.reason for s in signals],
            conflict_detected=conflict,
            resolution_strategy=strategies_used[0] if strategies_used else "none",
            persona_signals=signals,
        )

    def _confidence_weighted(self, signals: list[PersonaSignal]) -> tuple[str, float]:
        """Weight signals by confidence score."""
        action_scores = {"buy": 0.0, "hold": 0.0, "sell": 0.0, "warning": 0.0}

        for s in signals:
            if s.action in action_scores:
                action_scores[s.action] += s.confidence

        # Normalize by number of signals
        total = sum(action_scores.values())
        if total > 0:
            for k in action_scores:
                action_scores[k] /= len(signals)

        # Return highest scoring action
        best_action = max(action_scores, key=action_scores.get)
        best_confidence = action_scores[best_action]
        return best_action, best_confidence

    def _zettaranc_first(self, signals: list[PersonaSignal]) -> tuple[str, float]:
        """Zettaranc has final say on quantitative signals."""
        zettaranc_signal = None
        other_signals = []

        for s in signals:
            if s.persona == "zettaranc":
                zettaranc_signal = s
            else:
                other_signals.append(s)

        if zettaranc_signal:
            # If Zettaranc disagrees strongly with others, Z wins
            if other_signals:
                other_action = max(set(s.action for s in other_signals), key=lambda a: sum(1 for s in other_signals if s.action == a))
                if zettaranc_signal.action != other_action:
                    return zettaranc_signal.action, zettaranc_signal.confidence

            return zettaranc_signal.action, zettaranc_signal.confidence

        # Fallback to confidence weighted
        return self._confidence_weighted(signals)

    def _consensus(self, signals: list[PersonaSignal]) -> tuple[str, float]:
        """All personas must agree (majority wins)."""
        action_counts = {}
        for s in signals:
            action_counts[s.action] = action_counts.get(s.action, 0) + 1

        # Require at least 60% agreement
        max_count = max(action_counts.values())
        if max_count >= len(signals) * 0.6:
            best_action = max(action_counts, key=action_counts.get)
            return best_action, max_count / len(signals)

        # No consensus
        return "hold", 0.0

    def _most_bullish(self, signals: list[PersonaSignal]) -> tuple[str, float]:
        """Take the most bullish signal."""
        action_order = {"buy": 3, "hold": 2, "warning": 1, "sell": 0}

        best_signal = max(signals, key=lambda s: action_order.get(s.action, 0))
        return best_signal.action, best_signal.confidence
