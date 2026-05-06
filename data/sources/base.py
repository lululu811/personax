from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    name: str = ""
    priority: int = 999

    @abstractmethod
    def get_daily(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return standardized DataFrame with columns:
        code, trade_date, open, high, low, close, volume, amount, change_pct, turnover_rate, source
        """
        ...

    @abstractmethod
    def get_fund_flow(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return standardized DataFrame with columns:
        code, trade_date, main_in, main_out, main_net, retail_in, retail_out, retail_net, total_amount, source
        """
        ...

    @abstractmethod
    def get_stocks(self) -> pd.DataFrame:
        """Return all stock basic info."""
        ...

    def get_daily_basic(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return daily valuation metrics. Optional interface."""
        return pd.DataFrame()

    def get_income(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return income statement data. Optional interface."""
        return pd.DataFrame()

    def get_balancesheet(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return balance sheet data. Optional interface."""
        return pd.DataFrame()

    def get_cashflow(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return cash flow statement data. Optional interface."""
        return pd.DataFrame()

    def get_fina_indicator(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return financial indicators. Optional interface."""
        return pd.DataFrame()

    def get_adj_factor(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Return adjustment factor for price restoration. Optional interface."""
        return pd.DataFrame()
