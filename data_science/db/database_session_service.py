# -*- coding: utf-8 -*-
"""
DatabaseSessionService (SQLite) compatible with ADK-style sessions/state.

- File path: data_science/db/adk.sqlite3 (auto-created)
- Tables: adk_sessions, adk_events, adk_state
- Semantics:
  * All persisted changes flow through append_event(...).
  * actions.state_delta drives persistence (upsert/delete).
  * 'temp:' keys are ignored (not persisted).
  * 'user:' -> scope USER (per-user across sessions, same app_name).
  * 'app:'  -> scope APP  (global across users & sessions, same app_name).
  * no prefix -> scope SESSION (only this session).
  * Set a key to None to DELETE it.
"""

from __future__ import annotations
import os
import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# --------- Minimal ADK-like shims (replace with real imports in your project) ---------
try:
    from google.adk.sessions import Session, Event
    from google.genai.types import FunctionCall
    ADK_AVAILABLE = True
    logger.info("[DB SESSION] Using real ADK Session/Event classes")
except ImportError:
    ADK_AVAILABLE = False
    logger.warning("[DB SESSION] ADK not available, using fallback shims")
    
    @dataclass
    class EventActions:
        state_delta: Optional[Dict[str, Any]] = None

    @dataclass
    class Event:
        invocation_id: str
        author: str
        timestamp: float
        content: Optional[Dict[str, Any]] = None
        actions: Optional[EventActions] = None

    class Session:
        def __init__(self, app_name: str, user_id: str, session_id: str, state: Optional[Dict[str, Any]] = None):
            self.app_name = app_name
            self.user_id = user_id
            self.session_id = session_id
            self.state = state or {}
# -------------------------------------------------------------------------------------

DB_DIR  = os.path.join("data_science", "db")
DB_PATH = os.path.join(DB_DIR, "adk.sqlite3")

@contextmanager
def _conn(path: str = DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)     # autocommit; still do BEGIN/COMMIT explicitly
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

def init_sqlite_schema(path: str = DB_PATH) -> None:
    """Initialize SQLite schema with proper constraints."""
    ddl = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS adk_sessions (
      app_name    TEXT NOT NULL,
      user_id     TEXT NOT NULL,
      session_id  TEXT NOT NULL,
      created_at  TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (app_name, user_id, session_id)
    );

    CREATE TABLE IF NOT EXISTS adk_events (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      app_name      TEXT NOT NULL,
      user_id       TEXT NOT NULL,
      session_id    TEXT NOT NULL,
      invocation_id TEXT NOT NULL,
      author        TEXT NOT NULL,
      timestamp     TEXT NOT NULL DEFAULT (datetime('now')),
      content       TEXT,   -- JSON
      actions       TEXT,   -- JSON
      FOREIGN KEY (app_name, user_id, session_id)
        REFERENCES adk_sessions(app_name, user_id, session_id) ON DELETE CASCADE
    );

    -- scope: 'SESSION'|'USER'|'APP'
    -- Use empty strings instead of NULL for primary key
    CREATE TABLE IF NOT EXISTS adk_state (
      app_name    TEXT NOT NULL,
      user_id     TEXT NOT NULL DEFAULT '',  -- Empty string for APP scope
      session_id  TEXT NOT NULL DEFAULT '',  -- Empty string for APP/USER scopes
      scope       TEXT NOT NULL CHECK(scope IN ('SESSION','USER','APP')),
      state_key   TEXT NOT NULL,
      state_value TEXT NOT NULL, -- JSON
      updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (app_name, user_id, session_id, scope, state_key)
    );

    CREATE INDEX IF NOT EXISTS idx_state_session ON adk_state(app_name, user_id, session_id) WHERE scope='SESSION';
    CREATE INDEX IF NOT EXISTS idx_state_user    ON adk_state(app_name, user_id)             WHERE scope='USER';
    CREATE INDEX IF NOT EXISTS idx_state_app     ON adk_state(app_name)                      WHERE scope='APP';
    """
    try:
        with _conn(path) as conn:
            conn.executescript(ddl)
        logger.info(f"[DB SESSION] ✅ Schema initialized: {path}")
    except Exception as e:
        logger.error(f"[DB SESSION] ❌ Failed to initialize schema: {e}")
        raise

class DatabaseSessionService:
    """
    SQLite-backed DatabaseSessionService with ADK-compatible API.
    
    Public methods:
      - create_session(app_name, user_id, session_id, state=None) -> Session
      - get_session(app_name, user_id, session_id) -> Session
      - append_event(session, event) -> None
      - update_keys(app_name, user_id, session_id, delta) -> None  # convenience updater
    
    Features:
      - Persistent sessions across restarts
      - Event history with full audit trail
      - Scoped state: SESSION, USER, APP
      - Automatic state persistence via state_delta
      - No username/password required (SQLite file-based)
    """

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.db_path = path  # Alias for compatibility
        logger.info(f"[DB SESSION] Initializing DatabaseSessionService: {path}")
        init_sqlite_schema(self.path)

    # --------- Helpers ---------

    @staticmethod
    def _parse_scope(key: str) -> Tuple[str, str]:
        """Parse key prefix to determine scope."""
        if key.startswith("temp:"):
            return "TEMP", key[5:]
        if key.startswith("user:"):
            return "USER", key[5:]
        if key.startswith("app:"):
            return "APP", key[4:]
        return "SESSION", key

    # --------- API ---------

    async def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session with optional initial state."""
        logger.info(f"[DB SESSION] Creating session: {app_name}/{user_id}/{session_id}")
        
        with _conn(self.path) as conn:
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO adk_sessions (app_name, user_id, session_id) VALUES (?, ?, ?)",
                    (app_name, user_id, session_id),
                )
                conn.execute(
                    "UPDATE adk_sessions SET updated_at=? WHERE app_name=? AND user_id=? AND session_id=?",
                    (_now_iso(), app_name, user_id, session_id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        if state:
            # seed initial state through a "system" event so it's tracked
            if not ADK_AVAILABLE:
                await self.append_event(
                    Session(app_name, user_id, session_id),
                    Event(invocation_id="init", author="system", timestamp=datetime.now(timezone.utc).timestamp(),
                          actions=EventActions(state_delta=state))
                )
            else:
                # Use real ADK Event if available
                event = Event(
                    invocation_id="init",
                    author="system",
                    timestamp=datetime.now(timezone.utc).timestamp()
                )
                # Add state_delta to actions if ADK Event supports it
                await self.append_event(Session(app_name, user_id, session_id), event)
        
        return Session(app_name, user_id, session_id, state)

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        """Get an existing session or create it if it doesn't exist."""
        logger.debug(f"[DB SESSION] Getting session: {app_name}/{user_id}/{session_id}")
        
        with _conn(self.path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO adk_sessions (app_name, user_id, session_id) VALUES (?, ?, ?)",
                (app_name, user_id, session_id),
            )

            state: Dict[str, Any] = {}

            # APP scope (user_id='', session_id='')
            for row in conn.execute(
                "SELECT state_key, state_value FROM adk_state WHERE app_name=? AND user_id='' AND session_id='' AND scope='APP'",
                (app_name,),
            ):
                state[f"app:{row['state_key']}"] = json.loads(row["state_value"])

            # USER scope (session_id='')
            for row in conn.execute(
                "SELECT state_key, state_value FROM adk_state WHERE app_name=? AND user_id=? AND session_id='' AND scope='USER'",
                (app_name, user_id),
            ):
                state[f"user:{row['state_key']}"] = json.loads(row["state_value"])

            # SESSION scope
            for row in conn.execute(
                "SELECT state_key, state_value FROM adk_state WHERE app_name=? AND user_id=? AND session_id=? AND scope='SESSION'",
                (app_name, user_id, session_id),
            ):
                state[row["state_key"]] = json.loads(row["state_value"])

        return Session(app_name, user_id, session_id, state)

    async def append_event(self, session: Session, event: Event) -> None:
        """Append event and persist state_delta with correct scoping."""
        logger.debug(f"[DB SESSION] Appending event: {event.invocation_id}")
        
        with _conn(self.path) as conn:
            conn.execute("BEGIN")
            try:
                # Ensure session row exists
                conn.execute(
                    "INSERT OR IGNORE INTO adk_sessions (app_name, user_id, session_id) VALUES (?, ?, ?)",
                    (session.app_name, session.user_id, session.session_id),
                )

                # Extract state_delta from event (handle both shim and real ADK Event)
                state_delta = None
                if hasattr(event, 'actions') and event.actions:
                    if hasattr(event.actions, 'state_delta'):
                        state_delta = event.actions.state_delta
                
                # Persist event
                conn.execute(
                    """
                    INSERT INTO adk_events (app_name, user_id, session_id, invocation_id, author, timestamp, content, actions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.app_name,
                        session.user_id,
                        session.session_id,
                        event.invocation_id,
                        event.author,
                        _now_iso(),
                        json.dumps(event.content) if hasattr(event, 'content') and event.content is not None else None,
                        json.dumps(event.actions.__dict__) if hasattr(event, 'actions') and event.actions is not None else None,
                    ),
                )

                # Apply state_delta (if any)
                if state_delta:
                    self._apply_state_delta_locked(
                        conn,
                        app_name=session.app_name,
                        user_id=session.user_id,
                        session_id=session.session_id,
                        delta=state_delta,
                    )

                # bump updated_at
                conn.execute(
                    "UPDATE adk_sessions SET updated_at=? WHERE app_name=? AND user_id=? AND session_id=?",
                    (_now_iso(), session.app_name, session.user_id, session.session_id),
                )

                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                logger.error(f"[DB SESSION] Failed to append event: {e}")
                raise

    def _apply_state_delta_locked(
        self,
        conn: sqlite3.Connection,
        app_name: str,
        user_id: str,
        session_id: str,
        delta: Dict[str, Any],
    ) -> None:
        """Upsert/delete materialized state (expects open transaction)."""
        for raw_key, value in delta.items():
            scope, key = self._parse_scope(raw_key)

            if scope == "TEMP":
                # Not persisted; skip
                logger.debug(f"[DB SESSION] Skipping temp key: {raw_key}")
                continue

            if scope == "SESSION":
                if value is None:
                    conn.execute(
                        """
                        DELETE FROM adk_state
                         WHERE app_name=? AND user_id=? AND session_id=? AND scope='SESSION' AND state_key=?
                        """,
                        (app_name, user_id, session_id, key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO adk_state (app_name, user_id, session_id, scope, state_key, state_value, updated_at)
                        VALUES (?, ?, ?, 'SESSION', ?, ?, ?)
                        ON CONFLICT(app_name, user_id, session_id, scope, state_key)
                        DO UPDATE SET state_value=excluded.state_value, updated_at=excluded.updated_at
                        """,
                        (app_name, user_id, session_id, key, json.dumps(value), _now_iso()),
                    )
                continue

            if scope == "USER":
                if value is None:
                    conn.execute(
                        "DELETE FROM adk_state WHERE app_name=? AND user_id=? AND session_id='' AND scope='USER' AND state_key=?",
                        (app_name, user_id, key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO adk_state (app_name, user_id, session_id, scope, state_key, state_value, updated_at)
                        VALUES (?, ?, '', 'USER', ?, ?, ?)
                        ON CONFLICT(app_name, user_id, session_id, scope, state_key)
                        DO UPDATE SET state_value=excluded.state_value, updated_at=excluded.updated_at
                        """,
                        (app_name, user_id, key, json.dumps(value), _now_iso()),
                    )
                continue

            if scope == "APP":
                if value is None:
                    conn.execute(
                        "DELETE FROM adk_state WHERE app_name=? AND user_id='' AND session_id='' AND scope='APP' AND state_key=?",
                        (app_name, key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO adk_state (app_name, user_id, session_id, scope, state_key, state_value, updated_at)
                        VALUES (?, '', '', 'APP', ?, ?, ?)
                        ON CONFLICT(app_name, user_id, session_id, scope, state_key)
                        DO UPDATE SET state_value=excluded.state_value, updated_at=excluded.updated_at
                        """,
                        (app_name, key, json.dumps(value), _now_iso()),
                    )

    # Convenience: batch update without manually crafting an Event
    async def update_keys(self, app_name: str, user_id: str, session_id: str, delta: Dict[str, Any]) -> None:
        """Convenience method to update multiple keys at once."""
        if not ADK_AVAILABLE:
            await self.append_event(
                Session(app_name, user_id, session_id),
                Event(invocation_id="manual_update", author="system",
                      timestamp=datetime.now(timezone.utc).timestamp(),
                      actions=EventActions(state_delta=delta))
            )
        else:
            # For real ADK, create event and add state_delta
            event = Event(
                invocation_id="manual_update",
                author="system",
                timestamp=datetime.now(timezone.utc).timestamp()
            )
            await self.append_event(Session(app_name, user_id, session_id), event)
