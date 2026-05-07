"""Quant Technical Tools.

Pure computation tools for technical analysis.
Each tool is a standalone function/module that can be called by any Persona.

Usage:
    from tools.quant.technical import kdj, rsi_3, bbi

    result = kdj.compute(df)
    print(result.signals)  # {'b1': True, 'golden_cross': False}
"""

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    SignalType,
    TechnicalTool,
    register_tool,
    get_tool,
    list_tools,
)

# Core tools - lazy import to avoid circular deps
__all__ = [
    "OHLCV",
    "ToolResult",
    "SignalType",
    "TechnicalTool",
    "register_tool",
    "get_tool",
    "list_tools",
    # Tools
    "kdj",
    "rsi_3",
    "bbi",
    "stochastic",
    "macd",
    "bollinger",
    "atr",
]


def __getattr__(name: str):
    if name in ["kdj", "rsi_3", "bbi", "stochastic", "macd", "bollinger", "atr"]:
        import importlib
        return importlib.import_module(f"tools.quant.technical.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
