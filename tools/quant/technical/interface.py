"""Quant Technical Tools - Interface Contract.

This module defines the contract for all quantitative technical indicators.
Tools are pure computation - they receive DataFrames and return structured results.

CONTRACT:
- All tools accept: DataFrame with columns [open, high, low, close, vol]
- All tools return: dict with specific structure per tool
- Tool names are lowercase_underscore (e.g., kdj, rsi_3)
- No side effects, no state, pure functions

PERSONA LAYER accesses tools via:
    from tools.quant.technical import kdj, rsi_3, macd
    result = kdj.compute(df)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable
import pandas as pd


# =============================================================================
# Core Data Types
# =============================================================================

class SignalType(Enum):
    """Standardized signal types across all indicators."""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"
    WARNING = "warning"


@dataclass(frozen=True)
class ToolResult:
    """Standard wrapper for all tool computation results."""
    tool_name: str
    data: dict  # Tool-specific payload
    signals: dict[str, bool]  # Named boolean signals
    metadata: dict  # Additional context (e.g., params used)


@dataclass(frozen=True)
class OHLCV:
    """Standard input format for all technical tools."""
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    vol: pd.Series

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "OHLCV":
        required = ["open", "high", "low", "close", "vol"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        return cls(
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            vol=df["vol"],
        )


# =============================================================================
# Base Protocol for All Tools
# =============================================================================

@runtime_checkable
class TechnicalTool(Protocol):
    """Protocol that all technical indicator tools must implement."""

    @property
    def name(self) -> str:
        """Tool name in lowercase_underscore format."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this tool computes."""
        ...

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        """
        Compute the indicator.

        Args:
            data: Either OHLCV dataclass or DataFrame with [open, high, low, close, vol]

        Returns:
            ToolResult with tool_name, data payload, named signals, and metadata
        """
        ...


# =============================================================================
# Registry for Tool Discovery
# =============================================================================

_TOOL_REGISTRY: dict[str, TechnicalTool] = {}


def register_tool(tool: TechnicalTool) -> TechnicalTool:
    """Decorator to register a tool in the global registry."""
    _TOOL_REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> TechnicalTool:
    """Get a registered tool by name."""
    if name not in _TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}. Available: {list(_TOOL_REGISTRY.keys())}")
    return _TOOL_REGISTRY[name]


def list_tools() -> dict[str, TechnicalTool]:
    """List all registered tools."""
    return dict(_TOOL_REGISTRY)
