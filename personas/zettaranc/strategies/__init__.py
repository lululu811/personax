"""Zettaranc Strategies - Persona-specific trading strategies with registry.

These strategies use tools from tools/quant/technical/ layer.
Each strategy implements Z哥's specific trading concepts.

Usage:
    from personas.zettaranc.strategies import get_strategy, list_strategies

    strategy = get_strategy("b1")
    signal = strategy.detect(df)
    print(signal.action)  # "buy", "sell", "hold"
"""

import inspect
from typing import Type

from personas.zettaranc.strategies.b1 import B1Strategy, StrategySignal
from personas.zettaranc.strategies.b2_break import B2BreakStrategy
from personas.zettaranc.strategies.five_score import FiveScoreStrategy, FiveScoreResult
from personas.zettaranc.strategies.sb1_fake_fall import SB1FakeFallStrategy
from personas.zettaranc.strategies.s1_warning import S1WarningStrategy
from personas.zettaranc.strategies.half_release import HalfReleaseStrategy
from personas.zettaranc.strategies.ultimate_b1 import UltimateB1Strategy
from personas.zettaranc.strategies.super_b1 import SuperB1Strategy
from personas.zettaranc.strategies.single_needle_20 import SingleNeedle20Strategy
from personas.zettaranc.strategies.abnormal import AbnormalMovementStrategy
from personas.zettaranc.strategies.pit_target import PitTargetStrategy, PitTargetResult
from personas.zettaranc.strategies.three_waves import ThreeWavesStrategy, ThreeWavesResult
from personas.zettaranc.strategies.two_thirty import TwoThirtyRuleStrategy
from personas.zettaranc.strategies.pattern_strategies import (
    DoublePonytailStrategy,
    ThreeOutsideThreeStrategy,
    TopWindmillStrategy,
    ThreeQuartersVolumeStrategy,
    FakeBearishStrategy,
    DoubleGunStrategy,
    BuyExhaustionStrategy,
    LongShadowShortVolumeStrategy,
)

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
                pass  # Skip classes that can't be instantiated


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
    """List all registered strategies (name -> class mapping)."""
    return dict(_STRATEGY_REGISTRY)


# =============================================================================
# Keyword -> Strategy mapping (persona-specific)
# =============================================================================

QUERY_STRATEGIES = {
    "B1": ["b1"],
    "b1": ["b1"],
    "B2": ["b2_break"],
    "b2": ["b2_break"],
    "五分": ["five_score"],
    "五点": ["five_score"],
    "sb1": ["sb1"],
    "S1": ["s1"],
    "s1": ["s1"],
    "半仓": ["half_release"],
    "终极B1": ["ultimate_b1"],
    "超级B1": ["super_b1"],
    "单针": ["single_needle_20"],
    "补票": ["single_needle_20"],
    "异动": ["abnormal"],
    "坑口": ["pit_target"],
    "三波": ["three_waves"],
    "两个30": ["two_thirty"],
    "双马尾": ["double_ponytail"],
    "三外有三": ["three_outside_three"],
    "大风车": ["top_windmill"],
    "四分之三": ["three_quarters"],
    "假阴": ["fake_bearish"],
    "双枪": ["double_gun"],
    "买盘枯竭": ["buy_exhaustion"],
    "长阴短柱": ["long_shadow_short"],
}

__all__ = [
    # Registry
    "get_strategy",
    "list_strategies",
    "QUERY_STRATEGIES",
    # Core
    "B1Strategy",
    "B2BreakStrategy",
    "FiveScoreStrategy",
    "StrategySignal",
    # Additional
    "SB1FakeFallStrategy",
    "S1WarningStrategy",
    "HalfReleaseStrategy",
    "UltimateB1Strategy",
    "SuperB1Strategy",
    "SingleNeedle20Strategy",
    "AbnormalMovementStrategy",
    "PitTargetStrategy",
    "PitTargetResult",
    "ThreeWavesStrategy",
    "ThreeWavesResult",
    "TwoThirtyRuleStrategy",
    # Pattern strategies
    "DoublePonytailStrategy",
    "ThreeOutsideThreeStrategy",
    "TopWindmillStrategy",
    "ThreeQuartersVolumeStrategy",
    "FakeBearishStrategy",
    "DoubleGunStrategy",
    "BuyExhaustionStrategy",
    "LongShadowShortVolumeStrategy",
]
