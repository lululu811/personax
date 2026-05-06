import importlib
from datetime import datetime, timedelta
from typing import Type

from data.db import Database
from data.sources.base import DataSource
from shared.config import load_yaml


class SyncEngine:
    def __init__(self, persona_name: str | None = None):
        self.db = Database()
        self.sources = self._load_sources(persona_name)

    def _load_sources(self, persona_name: str | None = None) -> list[DataSource]:
        registry = load_yaml("data_sources")["data_sources"]
        sources = []

        for name, cfg in registry.items():
            if not cfg.get("enabled", False):
                continue
            if persona_name:
                from shared.config import get_persona_config
                allowed = get_persona_config(persona_name)["data_sources"]
                if name not in allowed:
                    continue

            module_path = cfg["module"]
            class_name = cfg["class"]
            mod = importlib.import_module(module_path)
            cls: Type[DataSource] = getattr(mod, class_name)
            instance = cls(cfg.get("config", {}))
            sources.append(instance)

        return sorted(sources, key=lambda s: s.priority)

    def sync_stock_daily(self, code: str):
        last_date = self.db.get_last_trade_date(code, "daily_prices")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20180101"
        end = datetime.now().strftime("%Y%m%d")

        if start > end:
            return 0

        for source in self.sources:
            try:
                df = source.get_daily(code, start, end)
                if not df.empty:
                    self.db.insert("daily_prices", df)
                    self.db.log_sync("daily_prices", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} daily: {e}")
                continue
        return 0

    def sync_stock_fund_flow(self, code: str):
        last_date = self.db.get_last_trade_date(code, "fund_flow")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20240101"
        end = datetime.now().strftime("%Y%m%d")

        if start > end:
            return 0

        for source in self.sources:
            try:
                df = source.get_fund_flow(code, start, end)
                if not df.empty:
                    self.db.insert("fund_flow", df)
                    self.db.log_sync("fund_flow", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} fund_flow: {e}")
                continue
        return 0

    def sync_stock(self, code: str):
        daily_count = self.sync_stock_daily(code)
        flow_count = self.sync_stock_fund_flow(code)
        return {"daily_prices": daily_count, "fund_flow": flow_count}

    def sync_stocks_list(self):
        for source in self.sources:
            try:
                df = source.get_stocks()
                if not df.empty:
                    self.db.insert("stocks", df)
                    self.db.log_sync("stocks", None, source.name, "", "", len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for stocks list: {e}")
                continue
        return 0
