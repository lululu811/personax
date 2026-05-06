import os
from pathlib import Path

import pandas as pd
import tushare as ts

from data.sources.base import DataSource

_DAILY_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "vol": "volume",
    "amount": "amount",
    "pct_chg": "change_pct",
    "turnover_rate": "turnover_rate",
}

_FUND_FLOW_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "main_buy": "main_in",
    "main_sell": "main_out",
    "main_net_amount": "main_net",
    "retail_buy": "retail_in",
    "retail_sell": "retail_out",
    "retail_net_amount": "retail_net",
    "total_amount": "total_amount",
}


class TushareSource(DataSource):
    name = "tushare"
    priority = 1

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        token = os.environ.get(cfg.get("token_env", "TUSHARE_TOKEN"))
        if not token:
            raise ValueError("TUSHARE_TOKEN not set in environment")

        ts.set_token(token)
        self.pro = ts.pro_api()
        url = cfg.get("base_url", "http://tsy.xiaodefa.cn")
        self.pro._DataApi__http_url = url

    def _standardize(self, df: pd.DataFrame, col_map: dict, source: str) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.rename(columns=col_map)
        df["source"] = source
        # Ensure all expected columns exist
        for col in col_map.values():
            if col not in df.columns:
                df[col] = None
        return df[list(col_map.values()) + ["source"]]

    def get_daily(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.daily(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _DAILY_COLS, "tushare")

    def get_fund_flow(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.moneyflow(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _FUND_FLOW_COLS, "tushare")

    def get_stocks(self) -> pd.DataFrame:
        df = self.pro.stock_basic(exchange="", list_status="L")
        df = df.rename(columns={
            "ts_code": "code",
            "name": "name",
            "industry": "industry",
            "market": "market",
            "list_date": "list_date",
        })
        df["is_active"] = True
        df["source"] = "tushare"
        return df[["code", "name", "industry", "market", "list_date", "is_active", "source"]]
