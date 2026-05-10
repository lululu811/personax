"""Shared data models for the orchestration layer.

Contains dataclasses used across personas and orchestration components.
"""

from dataclasses import dataclass


@dataclass
class StrategySignal:
    """Result of a strategy detection."""
    action: str          # "buy", "sell", "hold", "warning"
    confidence: float    # 0.0 - 1.0
    reason: str         # Human-readable explanation
    metadata: dict       # Additional details (e.g., J value, conditions met)
