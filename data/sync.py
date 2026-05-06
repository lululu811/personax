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

    def sync_stock_daily_basic(self, code: str):
        last_date = self.db.get_last_trade_date(code, "daily_basic")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20180101"
        end = datetime.now().strftime("%Y%m%d")
        if start > end:
            return 0
        for source in self.sources:
            try:
                df = source.get_daily_basic(code, start, end)
                if not df.empty:
                    self.db.insert("daily_basic", df)
                    self.db.log_sync("daily_basic", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} daily_basic: {e}")
                continue
        return 0

    def _sync_quarterly(self, code: str, table: str, method_name: str, default_start: str = "20180101"):
        """Sync quarterly financial data."""
        last_date = self.db.get_last_trade_date(code, table)
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = default_start
        end = datetime.now().strftime("%Y%m%d")
        if start > end:
            return 0
        for source in self.sources:
            try:
                method = getattr(source, method_name, None)
                if method is None:
                    continue
                df = method(code, start, end)
                if not df.empty:
                    self.db.insert(table, df)
                    self.db.log_sync(table, code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} {table}: {e}")
                continue
        return 0

    def sync_stock_income(self, code: str):
        return self._sync_quarterly(code, "income", "get_income")

    def sync_stock_balancesheet(self, code: str):
        return self._sync_quarterly(code, "balancesheet", "get_balancesheet")

    def sync_stock_cashflow(self, code: str):
        return self._sync_quarterly(code, "cashflow", "get_cashflow")

    def sync_stock_fina_indicator(self, code: str):
        return self._sync_quarterly(code, "fina_indicator", "get_fina_indicator")

    def sync_stock_adj_factor(self, code: str):
        last_date = self.db.get_last_trade_date(code, "adj_factor")
        if last_date:
            start = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        else:
            start = "20180101"
        end = datetime.now().strftime("%Y%m%d")
        if start > end:
            return 0
        for source in self.sources:
            try:
                df = source.get_adj_factor(code, start, end)
                if not df.empty:
                    self.db.insert("adj_factor", df)
                    self.db.log_sync("adj_factor", code, source.name, start, end, len(df))
                    return len(df)
            except Exception as e:
                print(f"Source {source.name} failed for {code} adj_factor: {e}")
                continue
        return 0

    def sync_stock(self, code: str):
        daily_count = self.sync_stock_daily(code)
        flow_count = self.sync_stock_fund_flow(code)
        basic_count = self.sync_stock_daily_basic(code)
        income_count = self.sync_stock_income(code)
        bs_count = self.sync_stock_balancesheet(code)
        cf_count = self.sync_stock_cashflow(code)
        fina_count = self.sync_stock_fina_indicator(code)
        adj_count = self.sync_stock_adj_factor(code)
        return {
            "daily_prices": daily_count,
            "fund_flow": flow_count,
            "daily_basic": basic_count,
            "income": income_count,
            "balancesheet": bs_count,
            "cashflow": cf_count,
            "fina_indicator": fina_count,
            "adj_factor": adj_count,
        }

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
