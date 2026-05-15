"""
SQLite-backed visitor and intake storage.

All writes are serialised through a threading.Lock so the module is safe to
call from both sync (to_thread) and async contexts without extra machinery.
The connection is created fresh for each operation — SQLite's file-level
locking is the real serialisation primitive; the Python lock just keeps the
check_same_thread=False flag honest in multi-threaded use.
"""

import sqlite3
import threading
import time
from pathlib import Path

from app.config import get_settings

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    settings = get_settings()
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _lock, _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                ip TEXT,
                city TEXT,
                region TEXT,
                country TEXT,
                isp TEXT,
                referrer TEXT,
                user_agent TEXT,
                path_chosen TEXT,
                first_seen REAL,
                last_seen REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intake (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                name TEXT,
                company TEXT,
                role TEXT,
                submitted_at REAL
            )
        """)
        conn.commit()


def upsert_session(
    session_id: str,
    ip: str,
    geo,  # GeoResult namedtuple/object with .city .region .country .isp
    referrer: str | None,
    user_agent: str | None,
    path_chosen: str | None = None,
) -> None:
    """Insert a new session row or update last_seen / path_chosen on an existing one."""
    now = time.time()
    with _lock, _conn() as conn:
        existing = conn.execute(
            "SELECT first_seen FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE sessions SET last_seen=?, path_chosen=COALESCE(?, path_chosen) WHERE id=?",
                (now, path_chosen, session_id),
            )
        else:
            conn.execute(
                """INSERT INTO sessions
                   (id, ip, city, region, country, isp, referrer, user_agent, path_chosen, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, ip,
                    getattr(geo, "city", None),
                    getattr(geo, "region", None),
                    getattr(geo, "country", None),
                    getattr(geo, "isp", None),
                    referrer, user_agent, path_chosen, now, now,
                ),
            )
        conn.commit()


def save_intake(
    session_id: str,
    name: str | None,
    company: str | None,
    role: str | None,
) -> None:
    """Persist a visitor's intake form submission."""
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO intake (session_id, name, company, role, submitted_at) VALUES (?,?,?,?,?)",
            (session_id, name, company, role, time.time()),
        )
        conn.commit()


def touch_session(session_id: str) -> None:
    """Update last_seen for an existing session without changing other fields."""
    with _lock, _conn() as conn:
        conn.execute(
            "UPDATE sessions SET last_seen=? WHERE id=?", (time.time(), session_id)
        )
        conn.commit()


def get_all_visitors() -> list[dict]:
    """Return all sessions with their latest intake submission (if any), newest first."""
    with _lock, _conn() as conn:
        rows = conn.execute("""
            SELECT
                s.id, s.ip, s.city, s.region, s.country, s.isp,
                s.referrer, s.user_agent, s.path_chosen,
                s.first_seen, s.last_seen,
                i.name, i.company, i.role, i.submitted_at as intake_at
            FROM sessions s
            LEFT JOIN intake i ON i.session_id = s.id
            ORDER BY s.last_seen DESC
        """).fetchall()
        return [dict(r) for r in rows]
