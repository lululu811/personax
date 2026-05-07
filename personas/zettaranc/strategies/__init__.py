"""Zettaranc Strategies - Persona-specific trading strategies.

These strategies use tools from tools/quant/technical/ layer.
Each strategy implements Z哥's specific trading concepts.

Usage:
    from personas.zettaranc.strategies import b1, b2_break, five_score

    signal = b1.detect(df)
    print(signal.action)  # "buy", "sell", "hold"
"""

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

__all__ = [
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
