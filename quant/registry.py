import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Callable, Dict, Any

_INDICATORS: Dict[str, Dict[str, Any]] = {}


def register_indicator(name: str, category: str = "other"):
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
    if name not in _INDICATORS:
        raise ValueError(f"Unknown indicator: {name}. Available: {list(_INDICATORS.keys())}")
    return _INDICATORS[name]["func"]


def list_indicators(category: str | None = None) -> Dict[str, Dict[str, Any]]:
    if category is None:
        return dict(_INDICATORS)
    return {k: v for k, v in _INDICATORS.items() if v["category"] == category}


def discover_indicators():
    """Auto-discover all indicators in quant/indicators/ package."""
    from quant import indicators
    pkg_path = Path(indicators.__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_"):
            continue
        importlib.import_module(f"quant.indicators.{module_name}")


def save_registry(path: Path | None = None):
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
