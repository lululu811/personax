"""Quant Indicator Registry - Adapter layer for tools/quant/technical/.

This module provides backward-compatible indicator discovery and registration.
Under the hood, it bridges to the new `tools.quant.technical` layer.

Usage:
    from quant.registry import discover_indicators, get_indicator, list_indicators

    discover_indicators()
    func = get_indicator("MACD")
    result = func(df)  # Returns dict of Series (old interface)
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Callable, Dict, Any

import pandas as pd

_INDICATORS: Dict[str, Dict[str, Any]] = {}

# Mapping from old indicator names to new tool names
_NAME_MAP = {
    "MACD": "macd",
    "RSI": "rsi_3",
    "KDJ": "kdj",
    "BBI": "bbi",
    "BOLLINGER": "bollinger",
    "ATR": "atr",
    "STOCHASTIC": "stochastic",
}


def _make_adapter(tool_cls):
    """Create adapter function wrapping new-tool class into old-tool interface.

    Old interface: func(df) -> pd.Series | dict[str, pd.Series]
    New interface: tool.compute(df) -> ToolResult
    """
    def adapter(df: pd.DataFrame):
        instance = tool_cls()
        result = instance.compute(df)
        # Return only the data payload (dict of Series) for backward compat
        return result.data

    # Copy metadata for introspection
    adapter.__name__ = tool_cls.__name__
    adapter.__doc__ = getattr(tool_cls, "description", tool_cls.__name__)
    return adapter


def register_indicator(name: str, category: str = "other"):
    """Decorator to register an indicator in the legacy registry."""
    def decorator(func: Callable) -> Callable:
        _INDICATORS[name] = {
            "func": func,
            "category": category,
            "module": func.__module__,
            "doc": func.__doc__ or "",
            "params": _extract_params(func),
        }
        return func
    return decorator


def _extract_params(func: Callable) -> Dict[str, Any]:
    sig = inspect.signature(func)
    params = {}
    for param_name, param in sig.parameters.items():
        if param_name == "df":
            continue
        params[param_name] = {
            "default": param.default if param.default is not inspect.Parameter.empty else None,
            "type": "float" if param.annotation == float else "int" if param.annotation == int else "any",
        }
    return params


def get_indicator(name: str) -> Callable:
    """Get an indicator function by name.

    Supports both old registry names and new tool names (case-insensitive).
    """
    # Exact match
    if name in _INDICATORS:
        return _INDICATORS[name]["func"]

    # Case-insensitive match
    name_upper = name.upper()
    for k, v in _INDICATORS.items():
        if k.upper() == name_upper:
            return v["func"]

    raise ValueError(
        f"Unknown indicator: {name}. "
        f"Available: {sorted(_INDICATORS.keys())}"
    )


def list_indicators(category: str | None = None) -> Dict[str, Dict[str, Any]]:
    """List all registered indicators."""
    if category is None:
        return dict(_INDICATORS)
    return {k: v for k, v in _INDICATORS.items() if v["category"] == category}


def discover_indicators():
    """Auto-discover indicators from both legacy and new architecture.

    1. Legacy: quant/indicators/ (kept for backward compatibility)
    2. New: tools/quant/technical/ (primary source)
    """
    # 1. Discover legacy indicators
    try:
        from quant import indicators
        pkg_path = Path(indicators.__file__).parent
        for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
            if module_name.startswith("_"):
                continue
            importlib.import_module(f"quant.indicators.{module_name}")
    except ImportError:
        pass

    # 2. Discover new-architecture tools and register with legacy names
    try:
        from tools.quant.technical.interface import list_tools
        for tool_name, tool_cls in list_tools().items():
            # Register under original lowercase name
            _INDICATORS[tool_name] = {
                "func": _make_adapter(tool_cls),
                "category": "technical",
                "module": tool_cls.__module__,
                "doc": getattr(tool_cls, "description", tool_cls.__name__),
                "params": {},
            }
            # Also register under uppercase alias for backward compat
            alias = tool_name.upper()
            if alias != tool_name and alias not in _INDICATORS:
                _INDICATORS[alias] = _INDICATORS[tool_name]

        # Register legacy name aliases (e.g., "RSI" -> "rsi_3")
        for legacy_name, new_name in _NAME_MAP.items():
            if new_name in _INDICATORS and legacy_name not in _INDICATORS:
                _INDICATORS[legacy_name] = _INDICATORS[new_name]
    except ImportError:
        pass


def save_registry(path: Path | None = None):
    """Save current registry to YAML."""
    import yaml
    path = path or Path(__file__).parent.parent / "registry" / "indicators.yaml"

    data = {
        "auto_discovered": {
            name: {
                "module": info["module"],
                "category": info["category"],
                "params": info["params"],
            }
            for name, info in _INDICATORS.items()
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
