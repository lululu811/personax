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
    "double_line",
    "brick_pattern",
    "vol_ratio",
]


def __getattr__(name: str):
    if name in ["kdj", "rsi_3", "bbi", "stochastic", "macd", "bollinger", "atr",
                "double_line", "brick_pattern", "vol_ratio"]:
        import importlib
        return importlib.import_module(f"tools.quant.technical.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Query keyword -> tool name mapping (persona-agnostic)
QUERY_TOOLS = {
    "kdj": ["kdj"],
    "rsi": ["rsi_3"],
    "bbi": ["bbi"],
    "macd": ["macd"],
    "布林": ["bollinger"],
    "bollinger": ["bollinger"],
    "atr": ["atr"],
    "随机": ["stochastic"],
    "stochastic": ["stochastic"],
    "双线": ["double_line"],
    "白线": ["double_line"],
    "黄线": ["double_line"],
    "砖形": ["brick_pattern"],
    "砖": ["brick_pattern"],
    "量比": ["vol_ratio"],
}
