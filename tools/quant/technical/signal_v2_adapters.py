"""SignalV2 adapters for existing technical indicators.

This module converts ToolResult from existing indicators (macd, rsi_3, etc.)
into SignalV2 format for use with the new signal aggregation system.
"""

import pandas as pd
from typing import Optional

from orchestration.signals.v2 import SignalV2, SignalAction


def macd_to_signal(df: pd.DataFrame) -> Optional[SignalV2]:
    """Convert MACD indicator to SignalV2.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        SignalV2 if golden_cross or dead_cross detected, None otherwise
    """
    from tools.quant.technical import macd

    result = macd.compute(df)
    signals = result.signals

    if signals.get("golden_cross"):
        return SignalV2(
            source="MACD",
            action=SignalAction.BUY,
            confidence=0.75,
            weight=0.7,
            tags=["技术", "趋势", "动量"]
        )
    elif signals.get("dead_cross"):
        return SignalV2(
            source="MACD",
            action=SignalAction.SELL,
            confidence=0.75,
            weight=0.7,
            tags=["技术", "趋势", "动量"]
        )
    elif signals.get("above_zero"):
        return SignalV2(
            source="MACD",
            action=SignalAction.BUY,
            confidence=0.5,
            weight=0.5,
            tags=["技术", "趋势"]
        )
    elif signals.get("below_zero"):
        return SignalV2(
            source="MACD",
            action=SignalAction.SELL,
            confidence=0.5,
            weight=0.5,
            tags=["技术", "趋势"]
        )
    return None


def rsi_to_signal(df: pd.DataFrame, period: int = 3) -> Optional[SignalV2]:
    """Convert RSI indicator to SignalV2.

    Args:
        df: DataFrame with OHLCV data
        period: RSI period (default 3 for Zettaranc style)

    Returns:
        SignalV2 if oversold or overbought, None otherwise
    """
    from tools.quant.technical import rsi_3

    tool = rsi_3.RSITool(period=period)
    result = tool.compute(df)
    signals = result.signals

    if signals.get("oversold"):
        return SignalV2(
            source=f"RSI({period})",
            action=SignalAction.BUY,
            confidence=0.8,
            weight=0.6,
            tags=["技术", "动量", "超卖"]
        )
    elif signals.get("overbought"):
        return SignalV2(
            source=f"RSI({period})",
            action=SignalAction.SELL,
            confidence=0.8,
            weight=0.6,
            tags=["技术", "动量", "超买"]
        )
    return None


def kdj_to_signal(df: pd.DataFrame) -> Optional[SignalV2]:
    """Convert KDJ indicator to SignalV2.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        SignalV2 if golden_cross or dead_cross detected, None otherwise
    """
    from tools.quant.technical import kdj

    result = kdj.compute(df)
    signals = result.signals

    if signals.get("b1"):  # KDJ 金叉
        return SignalV2(
            source="KDJ",
            action=SignalAction.BUY,
            confidence=0.7,
            weight=0.6,
            tags=["技术", "趋势"]
        )
    elif signals.get("b2"):  # KDJ 死叉
        return SignalV2(
            source="KDJ",
            action=SignalAction.SELL,
            confidence=0.7,
            weight=0.6,
            tags=["技术", "趋势"]
        )
    return None


def bollinger_to_signal(df: pd.DataFrame) -> Optional[SignalV2]:
    """Convert Bollinger Bands indicator to SignalV2.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        SignalV2 if price touches bands, None otherwise
    """
    from tools.quant.technical import bollinger

    result = bollinger.compute(df)
    signals = result.signals

    if signals.get("lower_touch"):
        return SignalV2(
            source="布林带",
            action=SignalAction.BUY,
            confidence=0.6,
            weight=0.5,
            tags=["技术", "波动"]
        )
    elif signals.get("upper_touch"):
        return SignalV2(
            source="布林带",
            action=SignalAction.SELL,
            confidence=0.6,
            weight=0.5,
            tags=["技术", "波动"]
        )
    return None
