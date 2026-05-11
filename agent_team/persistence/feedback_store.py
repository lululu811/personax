"""SQLite persistence for feedback and agent reputation."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


class FeedbackStore:
    """Stores user feedback and computes agent reputation scores."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".personax" / "feedback.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS feedback_scores (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    user_score REAL NOT NULL,
                    feedback_text TEXT,
                    query_tags TEXT,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_reputation (
                    agent_name TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    cumulative_score REAL DEFAULT 0.0,
                    sample_count INTEGER DEFAULT 0,
                    avg_score REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (agent_name, tag)
                );

                CREATE TABLE IF NOT EXISTS team_sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    team_template TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    closed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_agent ON feedback_scores(agent_name);
                CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_scores(session_id);
            """)
            conn.commit()

    def record_feedback(
        self,
        session_id: str,
        agent_name: str,
        user_score: float,
        feedback_text: str = "",
        query_tags: list[str] = None,
    ):
        feedback_id = str(uuid.uuid4())
        tags_json = json.dumps(query_tags or [])
        now = datetime.now().isoformat()

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO feedback_scores
                   (feedback_id, session_id, agent_name, user_score, feedback_text, query_tags, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (feedback_id, session_id, agent_name, user_score, feedback_text, tags_json, now),
            )

            # Update reputation per tag
            for tag in (query_tags or ["global"]):
                conn.execute(
                    """INSERT INTO agent_reputation (agent_name, tag, cumulative_score, sample_count, avg_score, last_updated)
                       VALUES (?, ?, ?, 1, ?, ?)
                       ON CONFLICT(agent_name, tag) DO UPDATE SET
                       cumulative_score = cumulative_score + excluded.cumulative_score,
                       sample_count = sample_count + 1,
                       avg_score = (cumulative_score + excluded.cumulative_score) / (sample_count + 1),
                       last_updated = excluded.last_updated""",
                    (agent_name, tag, user_score, user_score, now),
                )
            conn.commit()

    def get_agent_scores(self, agent_name: str, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM feedback_scores WHERE agent_name = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_agent_reputation(self, agent_name: str, tag: str = "global") -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_reputation WHERE agent_name = ? AND tag = ?",
                (agent_name, tag),
            ).fetchone()
            return dict(row) if row else None

    def get_weighted_scores(self, agent_name: str) -> dict[str, float]:
        """Get avg score per tag for an agent."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT tag, avg_score FROM agent_reputation WHERE agent_name = ?",
                (agent_name,),
            ).fetchall()
            return {row["tag"]: row["avg_score"] for row in rows}

    def record_session(self, session_id: str, query: str, team_template: str, status: str):
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO team_sessions (session_id, query, team_template, status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, query, team_template, status, now),
            )
            conn.commit()

    def update_session_status(self, session_id: str, status: str):
        with self._connect() as conn:
            closed_at = datetime.now().isoformat() if status == "closed" else None
            conn.execute(
                "UPDATE team_sessions SET status = ?, closed_at = ? WHERE session_id = ?",
                (status, closed_at, session_id),
            )
            conn.commit()
