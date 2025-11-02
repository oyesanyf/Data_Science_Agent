"""
Artifact registry for tracking and resolving saved models and files.
"""
import os
import json
import time
from typing import Optional, Dict, Any

def _index_path(root: str) -> str:
    """Get the path to the artifact index file."""
    return os.path.join(root, ".artifact_index.json")

def _load_index(root: str) -> Dict[str, Any]:
    """Load the artifact index from disk."""
    p = _index_path(root)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"artifacts": []}

def _save_index(root: str, idx: Dict[str, Any]):
    """Save the artifact index to disk."""
    with open(_index_path(root), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)

def register_labeled_artifact(root: str, path: str, label: str, meta: Optional[dict] = None):
    """Register an artifact with a label for later retrieval."""
    idx = _load_index(root)
    idx["artifacts"].append({
        "label": label,
        "path": path,
        "ts": time.time(),
        "meta": meta or {}
    })
    _save_index(root, idx)

def resolve_latest(root: str, label: str) -> Optional[Dict[str, Any]]:
    """Resolve the latest artifact by label."""
    idx = _load_index(root)
    cand = [a for a in idx["artifacts"] if a.get("label") == label]
    if not cand:
        return None
    cand.sort(key=lambda a: a["ts"], reverse=True)
    return cand[0]

def list_artifacts_by_label(root: str, label_pattern: str = "") -> list:
    """List all artifacts matching a label pattern."""
    idx = _load_index(root)
    if not label_pattern:
        return idx["artifacts"]
    return [a for a in idx["artifacts"] if label_pattern in a.get("label", "")]
