"""
Utility functions for safe file paths and session management.
"""
import os
import re
import time
from datetime import datetime

SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

def safe_filename(name: str, ext: str = "") -> str:
    """Create a safe filename by removing/replacing unsafe characters."""
    base = SAFE_CHARS.sub("_", str(name)).strip("._")
    if not base:
        base = f"file_{int(time.time())}"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return base + ext

def ensure_session_dir(state: dict, workspace_root: str, kind: str = "artifacts") -> str:
    """Ensure a session-scoped directory exists."""
    sid = (state or {}).get("session_id") or (state or {}).get("Session ID") or "default"
    sub = os.path.join(workspace_root, safe_filename(sid), kind)
    os.makedirs(sub, exist_ok=True)
    return sub
