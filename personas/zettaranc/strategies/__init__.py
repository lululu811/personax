"""Zettaranc Strategies - Persona-specific trading strategies.

These strategies use tools from tools/quant/technical/ layer.
Each strategy implements Z哥's specific trading concepts.

Usage:
    from personas.zettaranc.strategies import b1, b2_break, five_score

    signal = b1.detect(df)
    print(signal.action)  # "buy", "sell", "hold"
"""

from personas.zettaranc.strategies.b1 import B1Strategy
from personas.zettaranc.strategies.b2_break import B2BreakStrategy
from personas.zettaranc.strategies.five_score import FiveScoreStrategy

__all__ = [
    "B1Strategy",
    "B2BreakStrategy",
    "FiveScoreStrategy",
]
