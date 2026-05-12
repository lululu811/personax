from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from orchestration.signals.v2 import SignalV2, SignalAction


class ConflictHandler(Enum):
    """冲突解决策略"""
    RECENT_WINS = "recent_wins"
    HIGH_CONFIDENCE_WINS = "high_confidence_wins"
    WEIGHTED_VOTING = "weighted_voting"
    DEBATE_MODE = "debate_mode"


@dataclass
class AggregatedResult:
    action: SignalAction
    confidence: float
    reasoning: str
    signals: list[SignalV2]
    conflicts: list[tuple[str, str]]  # (action1, action2)
    metadata: dict = field(default_factory=dict)


class Aggregator:
    """信号聚合器 - 整合多个 SignalV2 生成综合信号"""

    def __init__(self, conflict_handler: ConflictHandler = ConflictHandler.RECENT_WINS):
        self.conflict_handler = conflict_handler

    def aggregate(self, signals: list[SignalV2]) -> AggregatedResult:
        """聚合信号列表，返回综合结果"""
        if not signals:
            return AggregatedResult(
                action=SignalAction.NEUTRAL,
                confidence=0.0,
                reasoning="无信号",
                signals=[],
                conflicts=[]
            )

        # 检测冲突
        actions = set(s.action for s in signals)
        has_conflict = SignalAction.BUY in actions and SignalAction.SELL in actions

        # 按标签分组
        tag_groups = {}
        for s in signals:
            for tag in s.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(s)

        # 聚合
        if has_conflict:
            final_action, confidence = self._resolve_conflict(signals)
            conflicts = [(SignalAction.BUY.value, SignalAction.SELL.value)]
        else:
            final_action, confidence = self._aggregate_no_conflict(signals)
            conflicts = []

        reasoning = self._build_reasoning(final_action, signals)

        return AggregatedResult(
            action=final_action,
            confidence=confidence,
            reasoning=reasoning,
            signals=signals,
            conflicts=conflicts,
            metadata={"handler": self.conflict_handler.value, "tag_groups": list(tag_groups.keys())}
        )

    def _resolve_conflict(self, signals: list[SignalV2]) -> tuple[SignalAction, float]:
        """解决 BUY/SELL 冲突"""
        if self.conflict_handler == ConflictHandler.RECENT_WINS:
            sorted_signals = sorted(signals, key=lambda s: s.timestamp, reverse=True)
            winner = sorted_signals[0]
            return winner.action, winner.confidence

        elif self.conflict_handler == ConflictHandler.HIGH_CONFIDENCE_WINS:
            winner = max(signals, key=lambda s: s.confidence * s.weight)
            return winner.action, winner.confidence

        elif self.conflict_handler == ConflictHandler.WEIGHTED_VOTING:
            scores = {SignalAction.BUY: 0.0, SignalAction.SELL: 0.0,
                      SignalAction.HOLD: 0.0, SignalAction.NEUTRAL: 0.0}
            for s in signals:
                scores[s.action] += s.confidence * s.weight
            best = max(scores, key=scores.get)
            return best, scores[best] / len(signals) if signals else 0.0

        elif self.conflict_handler == ConflictHandler.DEBATE_MODE:
            return SignalAction.HOLD, 0.5

        return SignalAction.NEUTRAL, 0.0

    def _aggregate_no_conflict(self, signals: list[SignalV2]) -> tuple[SignalAction, float]:
        """无冲突时聚合信号"""
        total_conf = sum(s.confidence for s in signals)
        avg_confidence = total_conf / len(signals) if signals else 0.0

        action_counts = {}
        for s in signals:
            action_counts[s.action] = action_counts.get(s.action, 0) + 1
        best_action = max(action_counts, key=action_counts.get)

        return best_action, avg_confidence

    def _build_reasoning(self, action: SignalAction, signals: list[SignalV2]) -> str:
        """生成聚合理由"""
        count = sum(1 for s in signals if s.action == action)
        sources = [s.source for s in signals if s.action == action]
        return f"{action.value.upper()} 信号来自 {', '.join(sources)}，共 {count} 个"