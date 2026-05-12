# orchestration/review/signal_history.py
import sqlite3
import json
import tempfile
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from orchestration.review.models import SignalEvent, SignalRecord, SignalAction


class SignalHistory:
    """信号历史存储"""

    def __init__(self, db_path: str = "~/.personax/review.db"):
        self._db_path_str = db_path
        if db_path.startswith(":memory"):
            self._is_memory = True
            # 使用临时文件模拟内存数据库，以支持多线程/多连接
            self._temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            self.db_path = Path(self._temp_file.name)
            self._temp_file.close()
        else:
            self._is_memory = False
            self._temp_file = None
            self.db_path = Path(db_path).expanduser()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """线程安全的连接获取"""
        return sqlite3.connect(str(self.db_path), check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT NOT NULL,
                price REAL NOT NULL,
                asset TEXT NOT NULL,
                tags TEXT,
                evaluated INTEGER DEFAULT 0,
                outcome TEXT,
                outcome_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_asset ON signal_history(asset)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON signal_history(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_evaluated ON signal_history(evaluated)")
        conn.commit()
        conn.close()

    def add(self, event: SignalEvent) -> int:
        """添加信号记录"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO signal_history (timestamp, source, action, confidence, reason, price, asset, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.source,
                event.action.value,
                event.confidence,
                event.reason,
                event.price,
                event.asset,
                json.dumps(event.tags)
            ))
            conn.commit()
            record_id = cursor.lastrowid
            return record_id
        finally:
            conn.close()

    def get_unevaluated(self) -> list[SignalRecord]:
        """获取未评估的信号"""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM signal_history WHERE evaluated = 0").fetchall()
            return [self._row_to_record(row) for row in rows]
        finally:
            conn.close()

    def mark_evaluated(self, record_id: int, outcome: str, outcome_price: float):
        """标记已评估"""
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE signal_history
                SET evaluated = 1, outcome = ?, outcome_price = ?
                WHERE id = ?
            """, (outcome, outcome_price, record_id))
            conn.commit()
        finally:
            conn.close()

    def get_by_period(self, start: date, end: date) -> list[SignalRecord]:
        """按时间段获取信号"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM signal_history
                WHERE date(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, (start.isoformat(), end.isoformat())).fetchall()
            return [self._row_to_record(row) for row in rows]
        finally:
            conn.close()

    def _row_to_record(self, row: tuple) -> SignalRecord:
        return SignalRecord(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            source=row[2],
            action=SignalAction(row[3]),
            confidence=row[4],
            reason=row[5],
            price=row[6],
            asset=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            evaluated=bool(row[9]),
            outcome=row[10],
            outcome_price=row[11],
            created_at=datetime.fromisoformat(row[12]) if row[12] else None
        )

    def close(self):
        """清理临时文件"""
        if self._temp_file:
            try:
                os.unlink(self._temp_file.name)
            except OSError:
                pass