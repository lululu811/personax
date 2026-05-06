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

_DAILY_BASIC_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "close": "close",
    "turnover_rate": "turnover_rate",
    "turnover_rate_f": "turnover_rate_f",
    "volume_ratio": "volume_ratio",
    "pe": "pe",
    "pe_ttm": "pe_ttm",
    "pb": "pb",
    "ps": "ps",
    "ps_ttm": "ps_ttm",
    "dv_ratio": "dv_ratio",
    "dv_ttm": "dv_ttm",
    "total_share": "total_share",
    "float_share": "float_share",
    "free_share": "free_share",
    "total_mv": "total_mv",
    "circ_mv": "circ_mv",
}

_INCOME_COLS = {
    "ts_code": "code",
    "end_date": "report_date",
    "comp_type": "report_type",
    "total_revenue": "revenue",
    "oper_cost": "operating_cost",
    "oper_profit": "operating_profit",
    "total_profit": "total_profit",
    "n_income": "net_profit",
    "n_income_attr_p": "net_profit_dedt",
    "basic_eps": "basic_eps",
    "diluted_eps": "diluted_eps",
    "int_income": "gross_profit",
    "fina_exp": "finance_cost",
    "income_tax": "income_tax",
    "rd_exp": "rd_expense",
    "t_compr_income": "total_compr_income",
}

_BALANCESHEET_COLS = {
    "ts_code": "code",
    "end_date": "report_date",
    "comp_type": "report_type",
    "total_assets": "total_assets",
    "total_liab": "total_liab",
    "total_hldr_eqy_exc_min_int": "total_equity",
    "total_cur_assets": "total_cur_assets",
    "total_cur_liab": "total_cur_liab",
    "money_cap": "money_cap",
    "trad_asset": "trad_asset",
    "inventories": "inventories",
    "fix_assets": "fix_assets",
    "intan_assets": "intan_assets",
    "goodwill": "goodwill",
    "total_nca": "total_nca",
    "total_ncl": "total_ncl",
    "notes_receiv": "notes_receiv",
    "accounts_receiv": "accounts_receiv",
}

_CASHFLOW_COLS = {
    "ts_code": "code",
    "end_date": "report_date",
    "comp_type": "report_type",
    "n_cashflow_act": "net_operate_cash_flow",
    "n_cashflow_inv_act": "net_invest_cash_flow",
    "n_cashflows_fin_act": "net_finance_cash_flow",
    "c_cash_equ_end_period": "cash_equ_end_period",
    "c_inf_fr_operate": "sales_service_cash",
    "c_paid_goods_s": "buy_service_cash",
    "c_paid_to_for_empl": "employ_cash",
    "c_pay_dist_dpcp_int_exp": "tax_pay_cash",
    "c_fr_sale_sg": "c_fr_sg",
    "c_inf_fr_operate_a": "c_inf_fr_operate",
    "c_paid_to_for_debt": "c_paid_for_debt",
}

_FINA_INDICATOR_COLS = {
    "ts_code": "code",
    "end_date": "report_date",
    "comp_type": "report_type",
    "eps": "eps",
    "dt_eps": "dt_eps",
    "bps": "bps",
    "roe": "roe",
    "roe_waa": "roe_waa",
    "roe_dt": "roe_dt",
    "roa": "roa",
    "roic": "roic",
    "grossprofit_margin": "grossprofit_margin",
    "netprofit_margin": "netprofit_margin",
    "debt_to_assets": "debt_to_assets",
    "current_ratio": "current_ratio",
    "quick_ratio": "quick_ratio",
    "ocf_to_or": "ocf_to_or",
    "salescash_to_or": "salescash_to_or",
    "basic_eps_yoy": "basic_eps_yoy",
    "netprofit_yoy": "netprofit_yoy",
    "dt_netprofit_yoy": "dt_netprofit_yoy",
    "tr_yoy": "tr_yoy",
    "or_yoy": "or_yoy",
    "rd_exp": "rd_exp",
    "q_netprofit_yoy": "q_netprofit_yoy",
    "q_roe": "q_roe",
    "q_grossprofit_margin": "q_grossprofit_margin",
    "q_netprofit_margin": "q_netprofit_margin",
}

_ADJ_FACTOR_COLS = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "adj_factor": "adj_factor",
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
        # Convert YYYYMMDD to YYYY-MM-DD for date columns
        for date_col in ["trade_date", "list_date", "report_date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
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

    def get_daily_basic(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.daily_basic(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _DAILY_BASIC_COLS, "tushare")

    def get_income(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.income(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _INCOME_COLS, "tushare")

    def get_balancesheet(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.balancesheet(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _BALANCESHEET_COLS, "tushare")

    def get_cashflow(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.cashflow(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _CASHFLOW_COLS, "tushare")

    def get_fina_indicator(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.fina_indicator(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _FINA_INDICATOR_COLS, "tushare")

    def get_adj_factor(self, code: str, start: str, end: str) -> pd.DataFrame:
        df = self.pro.adj_factor(ts_code=code, start_date=start, end_date=end)
        return self._standardize(df, _ADJ_FACTOR_COLS, "tushare")
