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

    def get_last_trade_date(self, code: str, table: str = "daily_prices") -> str | None:
        sql = f"""
            SELECT MAX(trade_date) as max_date FROM {table}
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

    def close(self):
        self.conn.close()
