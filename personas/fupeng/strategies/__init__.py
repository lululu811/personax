"""Fupeng Strategies - Macro-focused analysis strategies.

These strategies implement 付鹏's macro analysis frameworks:
- explosive_gold: 爆金币预警 (high certainty + low vol + leverage = flash crash)
- shrinking_circle: 缩圈抱团检测 (capital concentration / risk aversion)
- dumbbell: 哑铃策略信号 (defensive + offensive, avoid middle)

Usage:
    from personas.fupeng.strategies import get_strategy, list_strategies

    strategy = get_strategy("explosive_gold")
    signal = strategy.detect(df)
    print(signal.risk_level)
"""

import inspect
from typing import Type

from personas.fupeng.strategies.explosive_gold import ExplosiveGoldStrategy
from personas.fupeng.strategies.shrinking_circle import ShrinkingCircleStrategy
from personas.fupeng.strategies.dumbbell import DumbbellStrategy

# =============================================================================
# Strategy Registry (auto-discover from imported classes)
# =============================================================================

_STRATEGY_REGISTRY: dict[str, Type] = {}


def _auto_register():
    """Auto-discover and register all strategy classes in this module."""
    current_module = __import__(__name__, fromlist=[""])
    for name, obj in inspect.getmembers(current_module):
        if (
            inspect.isclass(obj)
            and hasattr(obj, "name")
            and callable(getattr(obj, "detect", None))
        ):
            try:
                inst = obj()
                _STRATEGY_REGISTRY[inst.name] = obj
            except Exception:
                pass

_auto_register()


def get_strategy(name: str):
    """Get a registered strategy class by name."""
    if name not in _STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {name}. "
            f"Available: {list(_STRATEGY_REGISTRY.keys())}"
        )
    return _STRATEGY_REGISTRY[name]()


def list_strategies() -> dict[str, Type]:
    """List all registered strategies."""
    return dict(_STRATEGY_REGISTRY)


# =============================================================================
# Keyword -> Strategy mapping
# =============================================================================

QUERY_STRATEGIES = {
    "爆金币": ["explosive_gold"],
    "闪崩": ["explosive_gold"],
    "预警": ["explosive_gold"],
    "缩圈": ["shrinking_circle"],
    "抱团": ["shrinking_circle"],
    "集中度": ["shrinking_circle"],
    "哑铃": ["dumbbell"],
    "高股息": ["dumbbell"],
    "红利": ["dumbbell"],
    "防御": ["dumbbell"],
    "进攻": ["dumbbell"],
}

__all__ = [
    "get_strategy",
    "list_strategies",
    "QUERY_STRATEGIES",
    "ExplosiveGoldStrategy",
    "ShrinkingCircleStrategy",
    "DumbbellStrategy",
]
