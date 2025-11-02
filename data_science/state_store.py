# data_science/state_store.py
"""
SQLite-backed state store for persisting UI events and session data.
Extends the in-memory state with durable storage.
"""
import json
import sqlite3
import os
import time
import logging
from typing import Any, List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path (configurable via environment)
DB_PATH = os.getenv("STATE_DB_PATH", "data_science/adk_state.db")

def init_db():
    """Initialize SQLite database with required tables."""
    try:
        # Ensure directory exists
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(DB_PATH) as con:
            # UI events table
            con.execute("""
            CREATE TABLE IF NOT EXISTS ui_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT,
              tool_name TEXT,
              payload_json TEXT,
              created_at TEXT
            )""")
            
            # Session metadata table
            con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
              session_id TEXT PRIMARY KEY,
              started_at TEXT,
              last_active_at TEXT,
              metadata_json TEXT
            )""")
            
            # Tool execution history
            con.execute("""
            CREATE TABLE IF NOT EXISTS tool_executions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT,
              tool_name TEXT,
              args_json TEXT,
              result_json TEXT,
              success INTEGER,
              duration_ms REAL,
              executed_at TEXT
            )""")
            
            con.commit()
        
        logger.info(f"[OK] State database initialized: {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize state database: {e}")
        return False

def save_ui_event(session_id: str, tool_name: str, blocks: List[Dict[str, Any]]):
    """Save a UI event to the database."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO ui_events(session_id, tool_name, payload_json, created_at) VALUES (?,?,?,?)",
                (session_id, tool_name, json.dumps(blocks), time.strftime("%Y-%m-%d %H:%M:%S"))
            )
            con.commit()
    except Exception as e:
        logger.warning(f"Failed to save UI event: {e}")

def get_ui_events(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve UI events for a session."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            cursor = con.execute(
                "SELECT * FROM ui_events WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to retrieve UI events: {e}")
        return []

def save_tool_execution(
    session_id: str,
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
    success: bool,
    duration_ms: float
):
    """Save tool execution history."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                """INSERT INTO tool_executions(session_id, tool_name, args_json, result_json, success, duration_ms, executed_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    session_id,
                    tool_name,
                    json.dumps(args, default=str),
                    json.dumps(result, default=str) if result else None,
                    1 if success else 0,
                    duration_ms,
                    time.strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            con.commit()
    except Exception as e:
        logger.warning(f"Failed to save tool execution: {e}")

def update_session(session_id: str, metadata: Optional[Dict[str, Any]] = None):
    """Update session metadata."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            # Check if session exists
            cursor = con.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing
                if metadata:
                    con.execute(
                        "UPDATE sessions SET last_active_at = ?, metadata_json = ? WHERE session_id = ?",
                        (now, json.dumps(metadata), session_id)
                    )
                else:
                    con.execute(
                        "UPDATE sessions SET last_active_at = ? WHERE session_id = ?",
                        (now, session_id)
                    )
            else:
                # Insert new
                con.execute(
                    "INSERT INTO sessions(session_id, started_at, last_active_at, metadata_json) VALUES (?,?,?,?)",
                    (session_id, now, now, json.dumps(metadata or {}))
                )
            con.commit()
    except Exception as e:
        logger.warning(f"Failed to update session: {e}")

def get_session_stats(session_id: str) -> Dict[str, Any]:
    """Get statistics for a session."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            # Tool execution counts
            cursor = con.execute(
                "SELECT tool_name, COUNT(*) as count FROM tool_executions WHERE session_id = ? GROUP BY tool_name",
                (session_id,)
            )
            tool_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Success rate
            cursor = con.execute(
                "SELECT COUNT(*) as total, SUM(success) as successful FROM tool_executions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            total, successful = row[0], row[1] or 0
            success_rate = (successful / total * 100) if total > 0 else 0
            
            return {
                "tool_counts": tool_counts,
                "total_executions": total,
                "successful_executions": successful,
                "success_rate": round(success_rate, 2)
            }
    except Exception as e:
        logger.warning(f"Failed to get session stats: {e}")
        return {}

def cleanup_old_sessions(days: int = 30):
    """Clean up sessions older than specified days."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            cutoff = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days * 86400))
            con.execute("DELETE FROM ui_events WHERE created_at < ?", (cutoff,))
            con.execute("DELETE FROM tool_executions WHERE executed_at < ?", (cutoff,))
            con.execute("DELETE FROM sessions WHERE last_active_at < ?", (cutoff,))
            con.commit()
            logger.info(f"Cleaned up sessions older than {days} days")
    except Exception as e:
        logger.warning(f"Failed to cleanup old sessions: {e}")

