"""SQLite logging for leak alerts and image analysis results."""

import sqlite3
from datetime import datetime
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "events.sqlite"


def _conn():
    return sqlite3.connect(str(_DB_PATH))


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                result TEXT NOT NULL
            )
            """
        )


def log_event(event_type: str, result: str) -> None:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(
            "INSERT INTO events (created_at, event_type, result) VALUES (?, ?, ?)",
            (now, event_type, result),
        )


def recent_events(limit: int = 50):
    init_db()
    with _conn() as c:
        cur = c.execute(
            "SELECT created_at, event_type, result FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()
