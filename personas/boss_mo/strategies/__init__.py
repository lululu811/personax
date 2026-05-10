"""BOSS墨策略 - 盘面交易分析策略。

基于BOSS墨心智模型的可程序化策略：
- rhythm: 涨一段跌一段节奏检测
- risk_reward: 盈亏比计算（点位>方向）
- secondary_high: 次高与分水岭识别（BOSS墨核心模型）

Usage:
    from personas.boss_mo.strategies import get_strategy, list_strategies

    strategy = get_strategy("rhythm")
    result = strategy.detect(df)
"""

import inspect
from typing import Type

from personas.boss_mo.strategies.rhythm import RhythmStrategy
from personas.boss_mo.strategies.risk_reward import RiskRewardStrategy
from personas.boss_mo.strategies.secondary_high import SecondaryHighStrategy

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
# Keyword -> strategy mapping
# =============================================================================

QUERY_STRATEGIES = {
    "涨一段": ["rhythm"],
    "跌一段": ["rhythm"],
    "节奏": ["rhythm"],
    "涨跌循环": ["rhythm"],
    "盈亏比": ["risk_reward"],
    "止损": ["risk_reward"],
    "点位": ["risk_reward"],
    "支撑": ["risk_reward"],
    "阻力": ["risk_reward"],
    "次高": ["secondary_high"],
    "前高": ["secondary_high"],
    "右脚": ["secondary_high"],
    "分水": ["secondary_high"],
    "分水岭": ["secondary_high"],
    "关键价位": ["secondary_high"],
}

__all__ = [
    "get_strategy",
    "list_strategies",
    "QUERY_STRATEGIES",
    "RhythmStrategy",
    "RiskRewardStrategy",
    "SecondaryHighStrategy",
]
