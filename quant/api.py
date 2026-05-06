from typing import List, Dict, Any

import pandas as pd

from data.db import Database
from quant.registry import get_indicator, list_indicators, discover_indicators
from shared.config import get_persona_config


class QuantAPI:
    def __init__(self, persona_name: str | None = None):
        self.db = Database()
        self.persona_name = persona_name
        discover_indicators()

        if persona_name:
            cfg = get_persona_config(persona_name)
            self.default_indicators = cfg.get("quant_overrides", {}).get("default_indicators", ["MA", "MACD", "RSI"])
        else:
            self.default_indicators = ["MA", "MACD", "RSI"]

    def analyze_stock(self, code: str, indicators: List[str] | None = None) -> Dict[str, Any]:
        indicators = indicators or self.default_indicators

        df_price = self.db.get_daily(code)
        if df_price.empty:
            return {"error": f"No price data found for {code}"}

        df_price = df_price.sort_values("trade_date")

        results = {}
        for name in indicators:
            try:
                func = get_indicator(name)
                result = func(df_price)

                if isinstance(result, pd.Series):
                    results[name] = {
                        "current": round(result.iloc[-1], 4) if not pd.isna(result.iloc[-1]) else None,
                        "previous": round(result.iloc[-2], 4) if len(result) > 1 and not pd.isna(result.iloc[-2]) else None,
                        "trend": "up" if result.iloc[-1] > result.iloc[-2] else "down" if result.iloc[-1] < result.iloc[-2] else "flat",
                    }
                elif isinstance(result, dict):
                    results[name] = {
                        key: round(series.iloc[-1], 4) if not pd.isna(series.iloc[-1]) else None
                        for key, series in result.items()
                    }
            except Exception as e:
                results[name] = {"error": str(e)}

        return {
            "code": code,
            "latest_date": str(df_price["trade_date"].iloc[-1]),
            "latest_close": round(df_price["close"].iloc[-1], 4),
            "indicators": results,
        }

    def backtest(self, code: str, start: str, end: str, initial_capital: float = 100000.0) -> Dict[str, Any]:
        df = self.db.get_daily(code, start, end)
        if df.empty:
            return {"error": f"No data for {code} in range {start} ~ {end}"}

        df = df.sort_values("trade_date").reset_index(drop=True)

        # Simple buy-and-hold benchmark
        initial_price = df["close"].iloc[0]
        final_price = df["close"].iloc[-1]
        shares = initial_capital / initial_price
        final_value = shares * final_price

        returns = (final_price - initial_price) / initial_price
        max_price = df["close"].max()
        min_price = df["close"].min()
        max_drawdown = (min_price - max_price) / max_price

        return {
            "code": code,
            "start": str(df["trade_date"].iloc[0]),
            "end": str(df["trade_date"].iloc[-1]),
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(returns * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "trades": 1,
        }

    def get_available_indicators(self) -> Dict[str, Any]:
        return list_indicators()
