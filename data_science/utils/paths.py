from __future__ import annotations
from pathlib import Path
import json
import re
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Use proper folder structure from large_data_config
try:
    from ..large_data_config import UPLOAD_ROOT, WORKSPACES_ROOT as CONFIG_WORKSPACES_ROOT
    REPO_ROOT = UPLOAD_ROOT
    WORKSPACES_ROOT = CONFIG_WORKSPACES_ROOT
except ImportError:
    # Fallback to current directory
    REPO_ROOT = Path.cwd()
    WORKSPACES_ROOT = REPO_ROOT / ".uploaded_workspaces"
    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)

MANIFEST_FILENAME = "manifest.json"


def _slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    # NO HASH - return clean name only (hash suffixes were causing duplicate folders)
    return name[:48] if name else "dataset"


def derive_dataset_slug(csv_path: Path | str) -> str:
    p = Path(csv_path)
    base = p.name
    # remove any numeric prefixes like 1761165274_
    base = re.sub(r"^\d{10,}_", "", base)
    base = re.sub(r"\.csv$", "", base, flags=re.I)
    return _slugify(base)


def workspace_dir(dataset_slug: str) -> Path:
    """
    Create workspace with 12-folder structure (matches artifact_manager.py).
    """
    d = WORKSPACES_ROOT / dataset_slug
    # Use SAME 12 folders as artifact_manager.py to prevent structure mismatch
    subdirs = [
        "uploads", "data", "models", "reports", "results",
        "plots", "metrics", "indexes", "logs", "tmp", "manifests", "unstructured"
    ]
    for subdir in subdirs:
        (d / subdir).mkdir(parents=True, exist_ok=True)
    return d


def manifest_path(dataset_slug: str) -> Path:
    return workspace_dir(dataset_slug) / MANIFEST_FILENAME


def load_manifest(dataset_slug: str) -> dict:
    mp = manifest_path(dataset_slug)
    if mp.exists():
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_manifest(dataset_slug: str, data: dict) -> None:
    mp = manifest_path(dataset_slug)
    mp.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_workspace(csv_path: Optional[str | Path]) -> Tuple[str, Path, Optional[Path]]:
    """
    Returns: (dataset_slug, workspace_path, default_csv_path_or_None)
    If csv_path is provided and exists, it becomes/overrides default in manifest.
    If not provided, tries to read default from manifest; if missing, returns None for default.
    """
    default_csv: Optional[Path] = None
    if csv_path:
        csvp = Path(csv_path)
        if not csvp.is_absolute():
            csvp = REPO_ROOT / csvp  # allow relative inputs
        if not csvp.exists():
            # allow callers to handle this
            dataset_slug = derive_dataset_slug(csvp.name)
            ws = workspace_dir(dataset_slug)
            man = load_manifest(dataset_slug)
            default_csv = Path(man.get("default_csv_path")) if man.get("default_csv_path") else None
            return dataset_slug, ws, default_csv
        dataset_slug = derive_dataset_slug(csvp)
        ws = workspace_dir(dataset_slug)
        man = load_manifest(dataset_slug)
        man["default_csv_path"] = str(csvp.resolve())
        save_manifest(dataset_slug, man)
        default_csv = csvp.resolve()
        # NOTE: Removed _global manifest save - this created orphaned "_global" folders
        # The artifact_manager.py system handles workspace creation properly
        return dataset_slug, ws, default_csv

    # No csv_path: Cannot create workspace without a file
    # This function should only be called when a csv_path is provided
    # Return None to indicate workspace creation failed
    logger.warning(f"[paths] ensure_workspace called without csv_path - workspace not created")
    return None, None, None


def resolve_csv(csv_path: Optional[str | Path], dataset_slug: Optional[str] = None, prefer_parquet: bool = False) -> Path:
    """
    CSV-only file resolver.
    
    Args:
        csv_path: Path to CSV file (or None to use default)
        dataset_slug: Optional dataset slug for workspace lookup
        prefer_parquet: IGNORED - deprecated, kept for compatibility
    
    Returns:
        Path to the CSV file
    """
    from .io import robust_read_table
    
    if csv_path:
        p = Path(csv_path)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.exists() and dataset_slug:
            candidate = workspace_dir(dataset_slug) / Path(csv_path).name
            if candidate.exists():
                # Reject Parquet files
                if candidate.suffix.lower() == '.parquet':
                    raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {candidate.name}")
                if robust_read_table(candidate, validate_only=True):
                    return candidate.resolve()
                else:
                    raise FileNotFoundError(
                        f"File exists but cannot be parsed (malformed or corrupted): {candidate.name}. "
                        "Try using robust_auto_clean_file() to fix formatting issues."
                    )
        if not p.exists():
            raise FileNotFoundError(f"File not found. Received: {csv_path}")
        
        # Reject Parquet files
        if p.suffix.lower() == '.parquet':
            raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {p.name}")
        
        if robust_read_table(p, validate_only=True):
            return p.resolve()
        else:
            raise FileNotFoundError(
                f"File exists but cannot be parsed (malformed or corrupted): {p.name}. "
                "Try using robust_auto_clean_file() to fix formatting issues."
            )

    # No csv_path and no dataset_slug: Cannot resolve file
    # NOTE: Removed _global fallback - this created orphaned "_global" folders
    # The artifact_manager.py system handles workspace resolution properly
    if not dataset_slug:
        raise FileNotFoundError(
            "No CSV path provided and no dataset slug available. "
            "Please provide a csv_path or ensure workspace is initialized via artifact_manager.ensure_workspace()"
        )
    man = load_manifest(dataset_slug)
    if man.get("default_csv_path"):
        p = Path(man["default_csv_path"])
        if p.exists():
            # Reject Parquet files
            if p.suffix.lower() == '.parquet':
                raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {p.name}")
            if robust_read_table(p, validate_only=True):
                return p.resolve()
            else:
                raise FileNotFoundError(
                    f"Default file exists but cannot be parsed (malformed or corrupted): {p.name}. "
                    "Try using robust_auto_clean_file() to fix formatting issues."
                )

    raise FileNotFoundError("No file resolved. Provide csv_path explicitly or upload and set a default.")


