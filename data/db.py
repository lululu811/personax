from pathlib import Path
import duckdb
import pandas as pd

_DB_PATH = Path(__file__).parent / "cache" / "market.duckdb"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(_DB_PATH)
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._init_tables()

    def _init_tables(self):
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.execute(f.read())

    def get_daily(self, code: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        sql = """
            SELECT * FROM daily_prices
            WHERE code = ?
            {start_filter}
            {end_filter}
            ORDER BY trade_date
        """.format(
            start_filter="AND trade_date >= ?" if start else "",
            end_filter="AND trade_date <= ?" if end else "",
        )
        params = [code]
        if start:
            params.append(start)
        if end:
            params.append(end)
        return self.conn.execute(sql, params).df()

    def get_fund_flow(self, code: str, days: int = 30) -> pd.DataFrame:
        sql = """
            SELECT * FROM fund_flow
            WHERE code = ?
              AND trade_date >= (SELECT MAX(trade_date) FROM fund_flow WHERE code = ?) - INTERVAL '%s days'
            ORDER BY trade_date
        """ % days
        return self.conn.execute(sql, [code, code]).df()

    def get_financials(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM financials
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_daily_basic(self, code: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        sql = """
            SELECT * FROM daily_basic
            WHERE code = ?
            {start_filter}
            {end_filter}
            ORDER BY trade_date
        """.format(
            start_filter="AND trade_date >= ?" if start else "",
            end_filter="AND trade_date <= ?" if end else "",
        )
        params = [code]
        if start:
            params.append(start)
        if end:
            params.append(end)
        return self.conn.execute(sql, params).df()

    def get_income(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM income
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_balancesheet(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM balancesheet
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_cashflow(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM cashflow
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_fina_indicator(self, code: str, limit: int = 8) -> pd.DataFrame:
        sql = """
            SELECT * FROM fina_indicator
            WHERE code = ?
            ORDER BY report_date DESC
            LIMIT ?
        """
        return self.conn.execute(sql, [code, limit]).df()

    def get_adj_factor(self, code: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
        sql = """
            SELECT * FROM adj_factor
            WHERE code = ?
            {start_filter}
            {end_filter}
            ORDER BY trade_date
        """.format(
            start_filter="AND trade_date >= ?" if start else "",
            end_filter="AND trade_date <= ?" if end else "",
        )
        params = [code]
        if start:
            params.append(start)
        if end:
            params.append(end)
        return self.conn.execute(sql, params).df()

    def get_last_trade_date(self, code: str, table: str = "daily_prices") -> str | None:
        # Financial tables use report_date instead of trade_date
        date_col = "report_date" if table in ("income", "balancesheet", "cashflow", "fina_indicator", "financials") else "trade_date"
        sql = f"""
            SELECT MAX({date_col}) as max_date FROM {table}
            WHERE code = ?
        """
        result = self.conn.execute(sql, [code]).fetchone()
        return result[0].strftime("%Y%m%d") if result and result[0] else None

    def check_data_gaps(self, code: str, table: str = "daily_prices") -> list[tuple[str, str]]:
        sql = f"""
            WITH dates AS (
                SELECT trade_date,
                       LAG(trade_date) OVER (ORDER BY trade_date) as prev_date
                FROM {table}
                WHERE code = ?
            )
            SELECT prev_date, trade_date
            FROM dates
            WHERE prev_date IS NOT NULL
              AND trade_date - prev_date > 1
            ORDER BY prev_date
        """
        return self.conn.execute(sql, [code]).fetchall()

    def insert(self, table: str, df: pd.DataFrame):
        if df.empty:
            return
        self.conn.register("df_temp", df)
        cols = ", ".join(df.columns)
        self.conn.execute(f"INSERT OR REPLACE INTO {table} ({cols}) SELECT {cols} FROM df_temp")
        self.conn.unregister("df_temp")

    def log_sync(self, table_name: str, code: str | None, data_source: str,
                 start_date: str, end_date: str, records_count: int,
                 status: str = "success", error_msg: str = ""):
        self.conn.execute("""
            INSERT INTO sync_log (table_name, code, data_source, start_date, end_date, records_count, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [table_name, code, data_source, start_date, end_date, records_count, status, error_msg])

    # ------------------ User Portfolio APIs ------------------

    def get_watchlist(self, persona_name: str = "zettaranc", status: str | None = None) -> pd.DataFrame:
        sql = "SELECT * FROM watchlist WHERE persona_name = ?"
        params = [persona_name]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY added_at DESC"
        return self.conn.execute(sql, params).df()

    def add_watchlist(self, code: str, name: str | None = None, category: str = "default",
                      notes: str = "", persona_name: str = "zettaranc"):
        self.conn.execute("""
            INSERT INTO watchlist (code, name, category, status, notes, persona_name)
            VALUES (?, ?, ?, 'active', ?, ?)
            ON CONFLICT (code, persona_name) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                status = 'active',
                notes = EXCLUDED.notes
        """, [code, name or code, category, notes, persona_name])

    def remove_watchlist(self, code: str, persona_name: str = "zettaranc"):
        self.conn.execute("""
            UPDATE watchlist SET status = 'removed' WHERE code = ? AND persona_name = ?
        """, [code, persona_name])

    def get_holdings(self, persona_name: str = "zettaranc", status: str | None = None) -> pd.DataFrame:
        sql = "SELECT * FROM holdings WHERE persona_name = ?"
        params = [persona_name]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC"
        return self.conn.execute(sql, params).df()

    def update_holding(self, code: str, shares: float, avg_cost: float | None = None,
                       current_price: float | None = None, sector: str | None = None,
                       notes: str = "", persona_name: str = "zettaranc"):
        market_value = shares * current_price if current_price else None
        pl_amount = market_value - shares * avg_cost if market_value and avg_cost else None
        pl_ratio = pl_amount / (shares * avg_cost) if pl_amount and avg_cost and avg_cost != 0 else None
        self.conn.execute("""
            INSERT INTO holdings
            (code, shares, avg_cost, current_price, market_value, pl_amount, pl_ratio,
             sector, status, notes, updated_at, persona_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now(), ?)
            ON CONFLICT (code, persona_name) DO UPDATE SET
                shares = EXCLUDED.shares,
                avg_cost = EXCLUDED.avg_cost,
                current_price = EXCLUDED.current_price,
                market_value = EXCLUDED.market_value,
                pl_amount = EXCLUDED.pl_amount,
                pl_ratio = EXCLUDED.pl_ratio,
                sector = EXCLUDED.sector,
                status = EXCLUDED.status,
                notes = EXCLUDED.notes,
                updated_at = now()
        """, [code, shares, avg_cost, current_price, market_value, pl_amount, pl_ratio,
              sector, 'holding' if shares > 0 else 'closed', notes, persona_name])

    def get_trades(self, code: str | None = None, persona_name: str = "zettaranc",
                   start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        sql = "SELECT * FROM trades WHERE persona_name = ?"
        params = [persona_name]
        if code:
            sql += " AND code = ?"
            params.append(code)
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY trade_date DESC, rowid DESC"
        return self.conn.execute(sql, params).df()

    def add_trade(self, trade_date: str, code: str, trade_type: str, shares: float,
                  price: float, fee: float = 0, tax: float = 0, name: str | None = None,
                  notes: str = "", persona_name: str = "zettaranc"):
        amount = shares * price
        total_cost = amount + fee + tax
        self.conn.execute("""
            INSERT INTO trades (trade_date, code, name, trade_type, shares, price, amount, fee, tax, total_cost, status, notes, persona_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?)
        """, [trade_date, code, name or code, trade_type, shares, price, amount, fee, tax, total_cost, notes, persona_name])

    def close(self):
        self.conn.close()
