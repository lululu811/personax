"""Context memory with SQLite persistence for multi-turn conversations and preference learning."""
import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from orchestration.signals.v2 import SignalAction


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    risk_tolerance: str = "medium"  # low, medium, high
    signal_preferences: dict = field(default_factory=dict)  # action -> score


@dataclass
class ConversationContext:
    session_id: str
    history: list[Turn] = field(default_factory=list)
    user_profile: UserProfile = field(default_factory=UserProfile)
    asset_focus: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class ContextMemory:
    """SQLite-backed context memory for conversation history and user preferences."""

    def __init__(self, db_path: str = "~/.personax/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a shared connection, creating tables if needed."""
        if self._conn is None:
            if str(self.db_path) == ":memory:" or str(self.db_path).startswith("file::memory"):
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            else:
                self._conn = sqlite3.connect(self.db_path)
            self._init_db(self._conn)
        return self._conn

    def _init_db(self, conn: Optional[sqlite3.Connection] = None):
        """Initialize database tables."""
        if conn is None:
            conn = self._get_conn()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                data TEXT,
                created_at TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                action TEXT,
                accepted INTEGER,
                timestamp TIMESTAMP
            )"""
        )
        conn.commit()

    def save(self, ctx: ConversationContext):
        """Save conversation context to database."""
        conn = self._get_conn()
        data = {
            "history": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in ctx.history
            ],
            "user_profile": {
                "risk_tolerance": ctx.user_profile.risk_tolerance,
                "signal_preferences": ctx.user_profile.signal_preferences,
            },
            "asset_focus": ctx.asset_focus,
        }
        conn.execute(
            "INSERT OR REPLACE INTO conversations (session_id, data, created_at) VALUES (?, ?, ?)",
            (ctx.session_id, json.dumps(data), ctx.created_at.isoformat()),
        )
        conn.commit()

    def load(self, session_id: str) -> Optional[ConversationContext]:
        """Load conversation context from database."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        history = [Turn(**t) for t in data.get("history", [])]
        profile = UserProfile(**data.get("user_profile", {}))
        return ConversationContext(
            session_id=session_id,
            history=history,
            user_profile=profile,
            asset_focus=data.get("asset_focus", []),
        )

    def record_feedback(self, session_id: str, action: SignalAction, accepted: bool):
        """Record user feedback for signal actions to learn preferences."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO user_feedback (session_id, action, accepted, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, action.value, int(accepted), datetime.now().isoformat()),
        )
        conn.commit()

    def get_user_profile(self, session_id: str) -> UserProfile:
        """Get user profile, optionally updated with learned preferences."""
        ctx = self.load(session_id)
        if ctx:
            return ctx.user_profile
        return UserProfile()

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
