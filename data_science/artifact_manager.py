# data_science/artifact_manager.py
import os, json, shutil, time, re, logging, hashlib, tempfile
from pathlib import Path
from typing import Dict, Any, Iterable, Optional
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Export public API
__all__ = [
    'ensure_workspace',
    'get_workspace_subdir',
    'derive_dataset_slug',
    'rehydrate_session_state',
    'register_artifact',
    'register_and_sync_artifact',
    'route_artifacts_from_result',
    'list_artifacts',
    'resolve_latest',
    'get_workspace_info',
    '_try_recover_workspace_state',  # Recovery function for resilience
    'ensure_artifact_fallbacks',  # [FIX #22] Idempotent guard for artifact operations
]

# Artifact registry with versioning - SCOPED BY DATASET
_ARTIFACTS = []              # [{path, kind, label, version, created_at, dataset}]
_LATEST_BY_LABEL = defaultdict(dict)  # dataset -> label -> {path, version}
_VERSIONS_BY_LABEL = defaultdict(lambda: defaultdict(int))  # dataset -> label -> last_version

# NEW: configurable mode, default "copy" to preserve UI behavior
_ARTIFACT_ROUTING_MODE = os.getenv("ARTIFACT_ROUTING_MODE", "copy").lower()  # "copy" | "move"
if _ARTIFACT_ROUTING_MODE not in ("copy", "move"):
    _ARTIFACT_ROUTING_MODE = "copy"

# Root for workspaces; defaults under UPLOAD_ROOT/_workspaces
def _get_workspaces_root(upload_root: str) -> Path:
    """
    Get workspaces root path. Ensures it's under .uploaded/_workspaces (not uploaded/_workspaces).
    
    Args:
        upload_root: Upload root path (string) - should be .uploaded
    """
    # Convert to Path if string, ensure it's resolved
    upload_path = Path(upload_root).resolve()
    
    # CRITICAL: Validate that upload_root contains .uploaded (with dot)
    # This prevents accidentally using "uploaded" without the dot
    upload_str = str(upload_path)
    if not (upload_str.endswith(".uploaded") or ".uploaded" in upload_str or 
            upload_path.name == ".uploaded"):
        # Check if there's an .uploaded directory - if so, use it
        parent = upload_path.parent
        dot_uploaded = parent / ".uploaded"
        if dot_uploaded.exists() and dot_uploaded.is_dir():
            logger.warning(f"[PATH VALIDATION] Found .uploaded directory at {dot_uploaded}, using it instead of {upload_path}")
            upload_path = dot_uploaded
    
    # Construct workspaces root
    workspaces_path = upload_path / "_workspaces"
    
    # Use environment variable if set, otherwise use constructed path
    env_workspaces = os.getenv("WORKSPACES_ROOT")
    if env_workspaces:
        return Path(env_workspaces).resolve()
    
    return workspaces_path.resolve()

# Normalize a safe slug (dataset/run/tool)
def _slug(s: str, fallback: str) -> str:
    if not s:
        return fallback
    s = re.sub(r'[^a-zA-Z0-9_.-]+', '_', s.strip())
    return s or fallback


# [FIX #22] Fallback utilities for bulletproof artifact discovery
# ============================================================================

def _safe_get_upload_root() -> str:
    """Get UPLOAD_ROOT with graceful fallback."""
    try:
        from .large_data_config import UPLOAD_ROOT as _UPLOAD_ROOT  # type: ignore
    except Exception:
        _UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", ".uploads")
    return _UPLOAD_ROOT


def _scan_recent_files(paths: Iterable[str],
                       exts: Iterable[str],
                       *,
                       max_count: int = 50) -> list[Path]:
    """Scan multiple directories for files with given extensions, return newest first."""
    found: list[Path] = []
    for base in {p for p in paths if p and os.path.isdir(p)}:
        for ext in set(e.lower().strip().lstrip(".") for e in exts if e):
            try:
                found += list(Path(base).rglob(f"*.{ext}"))
            except Exception:
                continue
    # Files only, no symlinks; newest first
    out = [p for p in found if p.is_file() and not p.is_symlink()]
    out.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return out[:max_count]


def _fallback_exts() -> list[str]:
    """Get list of file extensions to scan for in fallback artifact discovery."""
    env = os.getenv("ARTIFACTS_FALLBACK_EXTS", "")
    if env.strip():
        return [e.strip().lstrip(".") for e in env.split(",") if e.strip()]
    # Sensible defaults cover most tool outputs
    return ["pdf","png","jpg","jpeg","svg","html","json","csv","parquet","txt","md","gif","webp","feather"]


def _maybe_label_for_suffix(path: Path) -> str:
    """Guess artifact type label from file extension."""
    s = path.suffix.lower()
    if s in (".png",".jpg",".jpeg",".svg",".gif",".webp"): 
        return "plot"
    if s in (".pdf",".html"): 
        return "report"
    if s in (".json",): 
        return "metrics"
    if s in (".parquet",".feather",".csv",".txt"): 
        return "data"
    return "other"

# ---------------------- Dataset naming (centralized) ----------------------
def _is_generic_uploaded(name: str) -> bool:
    n = (name or "").strip().lower()
    return n == "uploaded" or n.startswith("uploaded_")

def _sanitize_name(name: str, fallback: str = "uploaded") -> str:
    if not name:
        return fallback
    s = re.sub(r'[^a-zA-Z0-9_-]+', '_', name).strip('_')
    return s or fallback

def _llm_suggest_slug(headers: list[str], sample_summary: str = "") -> str | None:
    enable = os.getenv("ENABLE_LLM_NAMING", "0").lower() in ("1", "true", "yes")
    if not enable:
        return None
    try:
        model = os.getenv("LLM_NAMING_MODEL", "gpt-4o-mini")
        # Lazy import to avoid startup cost
        try:
            from litellm import completion
            use_litellm = True
        except Exception:
            use_litellm = False
        prompt = (
            "You are to propose a short, filesystem-safe dataset slug (lowercase, words separated by underscores, "
            "<= 40 chars, no spaces) based on CSV headers and a tiny summary. Return ONLY the slug.\n\n"
            f"Headers: {headers}\n\nSummary: {sample_summary}\n\nSlug:"
        )
        if use_litellm:
            resp = completion(model=model, messages=[{"role": "user", "content": prompt}])
            slug = resp.choices[0].message["content"].strip()  # type: ignore
        else:
            # Fallback to OpenAI SDK if available
            try:
                from openai import OpenAI
                cli = OpenAI()
                resp = cli.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
                slug = resp.choices[0].message.content.strip()
            except Exception:
                return None
        slug = _sanitize_name(slug.lower())[:40]
        if _is_generic_uploaded(slug):
            return None
        return slug
    except Exception:
        return None

def derive_dataset_slug(callback_state: Dict[str, Any], *, headers: list[str] | None = None, filepath: str | None = None, sample_summary: str = "", display_name: str | None = None) -> str:
    """Derive a dataset slug using, in order: existing state, display_name, LLM (optional), headers, filepath, or fallback.
    The resulting slug is written back to state under 'original_dataset_name'."""
    # 0) Existing
    existing = str(callback_state.get("original_dataset_name", ""))
    if existing and not _is_generic_uploaded(existing):
        slug = _sanitize_name(existing)
        callback_state["original_dataset_name"] = slug
        return slug

    # 0.5) Try display_name first (usually contains original filename from upload)
    if display_name:
        # Extract from display_name (e.g., "car_crashes.csv" from "1761964200_uploaded.csv")
        display_base = Path(display_name).stem
        # Remove timestamp patterns from display_name too
        display_base = re.sub(r"^uploaded_\d+_", "", display_base)
        display_base = re.sub(r"^\d{10,}_", "", display_base)
        display_base = _sanitize_name(display_base)
        if display_base and not _is_generic_uploaded(display_base) and display_base != "uploaded":
            callback_state["original_dataset_name"] = display_base
            logger.info(f"[DATASET NAME] Extracted from display_name: {display_base}")
            return display_base

    # 1) Filepath basename (check BEFORE headers - filepath is more specific than column names)
    if filepath:
        base = Path(filepath).stem
        # Handle pattern: TIMESTAMP_uploaded.csv -> try to extract from elsewhere
        # First try standard patterns
        base = re.sub(r"^uploaded_\d+_", "", base)
        base = re.sub(r"^\d{10,}_", "", base)
        # If still generic, try reverse pattern: \d+_uploaded -> check if there's more
        if _is_generic_uploaded(base):
            # Pattern might be: 1761964200_uploaded -> try to find original in parent path or state
            pass
        base = _sanitize_name(base)
        if not _is_generic_uploaded(base):
            callback_state["original_dataset_name"] = base
            logger.info(f"[DATASET NAME] Extracted from filepath: {base}")
            return base

    # 2) LLM suggestion (if enabled and headers provided)
    if headers:
        llm_slug = _llm_suggest_slug(headers, sample_summary=sample_summary)
        if llm_slug and not _is_generic_uploaded(llm_slug):
            callback_state["original_dataset_name"] = llm_slug
            logger.info(f"[DATASET NAME] LLM suggested: {llm_slug}")
            return llm_slug

    # 3) Headers-based slug (fallback if filepath was generic)
    if headers:
        # Try to find a meaningful header name (skip generic columns like 'id', 'index', 'unnamed')
        meaningful_headers = [h for h in headers[:5] if h.lower() not in ['id', 'index', 'unnamed', 'row', 'key']]
        if meaningful_headers:
            # Use first meaningful header or combine first 2-3
            joined = "_".join(_sanitize_name(h) for h in meaningful_headers[:2])[:40]
            if joined and len(joined) >= 3 and not _is_generic_uploaded(joined):
                callback_state["original_dataset_name"] = joined
                logger.info(f"[DATASET NAME] Derived from headers: {joined}")
                return joined
        # Fallback: use first 3 headers anyway
        joined = "_".join(_sanitize_name(h) for h in headers[:3])[:40]
        if joined and not _is_generic_uploaded(joined):
            callback_state["original_dataset_name"] = joined
            logger.info(f"[DATASET NAME] Derived from headers (fallback): {joined}")
            return joined

    # 4) Fallback
    callback_state["original_dataset_name"] = "uploaded"
    logger.warning(f"[DATASET NAME] Using fallback 'uploaded' - could not derive meaningful name from filepath={filepath}, display_name={display_name}, headers={headers[:3] if headers else None}")
    return "uploaded"

def _validate_upload_root(upload_root: str) -> None:
    """
    Ensure UPLOAD_ROOT exists and is writable.
    """
    try:
        os.makedirs(upload_root, exist_ok=True)
        if not os.access(upload_root, os.W_OK):
            raise RuntimeError(f"UPLOAD_ROOT is not writable: {upload_root}")
    except Exception as e:
        logger.error(f"Failed to validate UPLOAD_ROOT '{upload_root}': {e}")
        raise


def _cleanup_duplicate_files_in_workspace(workspace_paths: dict) -> int:
    """
    CRITICAL: Remove all duplicate files, keeping only the OLDEST file per unique content.
    
    This ensures:
    1. Only ONE file exists per unique content (by hash)
    2. The OLDEST file is always kept (by modification time)
    3. All newer duplicates are deleted
    
    Args:
        workspace_paths: Dict with workspace subdirectory paths (must have 'uploads' key)
    
    Returns:
        Number of duplicate files deleted
    """
    import hashlib
    from collections import defaultdict
    
    deleted_count = 0
    uploads_dir = workspace_paths.get("uploads") if isinstance(workspace_paths, dict) else None
    
    if not uploads_dir or not Path(uploads_dir).exists():
        return 0
    
    try:
        uploads_path = Path(uploads_dir)
        all_csvs = list(uploads_path.glob("*.csv"))
        
        if len(all_csvs) <= 1:
            return 0  # No duplicates possible
        
        # Group files by size (fast initial filter)
        files_by_size = defaultdict(list)
        for csv_file in all_csvs:
            try:
                size = csv_file.stat().st_size
                files_by_size[size].append(csv_file)
            except Exception:
                continue
        
        # For each size group, check content hashes and keep only oldest
        for size, files_list in files_by_size.items():
            if len(files_list) <= 1:
                continue  # No duplicates at this size
            
            # Group by content hash
            files_by_hash = defaultdict(list)
            for csv_file in files_list:
                try:
                    with open(csv_file, "rb") as f:
                        content_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                    files_by_hash[content_hash].append(csv_file)
                except Exception as e:
                    logger.debug(f"[CLEANUP] Could not hash {csv_file.name}: {e}")
                    continue
            
            # For each hash group with multiple files, keep only oldest
            for content_hash, hash_files in files_by_hash.items():
                if len(hash_files) > 1:
                    # Sort by modification time (oldest first)
                    hash_files.sort(key=lambda f: f.stat().st_mtime)
                    oldest = hash_files[0]
                    
                    # Delete all duplicates except oldest
                    for duplicate in hash_files[1:]:
                        try:
                            duplicate.unlink()
                            deleted_count += 1
                            logger.info(f"[CLEANUP] ✅ Deleted duplicate: {duplicate.name} (kept oldest: {oldest.name})")
                        except Exception as e:
                            logger.warning(f"[CLEANUP] Could not delete duplicate {duplicate.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"[CLEANUP] ✅ Cleaned up {deleted_count} duplicate file(s), kept oldest files only")
            print(f"✅ Removed {deleted_count} duplicate file(s), kept oldest")
    
    except Exception as e:
        logger.warning(f"[CLEANUP] Error during duplicate cleanup: {e}")
    
    return deleted_count


def ensure_workspace(callback_state: Dict[str, Any], upload_root: Any) -> Path:
    """
    Ensure a workspace exists for the current session/dataset.
    Creates:
      {WORKSPACES_ROOT}/{dataset_slug}/{run_id}/
        ├─ uploads/  ├─ data/   ├─ models/   ├─ reports/   ├─ results/
        ├─ plots/    ├─ metrics/├─ indexes/  ├─ logs/
        └─ tmp/      └─ manifests/
    Saves paths into callback_state for global use.
    
    Folder purposes:
    - reports/  : Markdown execution logs and PDF reports
    - results/  : Structured JSON tool outputs (for executive report)
    - plots/    : Visualizations (PNG, SVG, etc.)
    - models/   : Trained models (.joblib, .pkl, etc.)
    - metrics/  : Performance metrics (JSON)
    - data/     : Processed/cleaned datasets
    
    Args:
        callback_state: State dictionary containing workspace info
        upload_root: Upload root path (Path object or string) - MUST be .uploaded (with dot)
    """
    # [CRITICAL FIX] Convert Path object to string if needed, ensure it's .uploaded (not uploaded)
    from pathlib import Path as PathType
    if isinstance(upload_root, PathType):
        upload_root_str = str(upload_root.resolve())
    else:
        upload_root_str = str(upload_root)
    
    # [CRITICAL] Validate path contains .uploaded (with dot) - never allow "uploaded" without dot
    upload_path_obj = Path(upload_root_str).resolve()
    if upload_path_obj.name != ".uploaded" and ".uploaded" not in str(upload_path_obj):
        # Try to find .uploaded in parent directory
        parent_dir = upload_path_obj.parent
        dot_uploaded_candidate = parent_dir / ".uploaded"
        if dot_uploaded_candidate.exists() and dot_uploaded_candidate.is_dir():
            logger.warning(f"[PATH ENFORCEMENT] upload_root was '{upload_root_str}' but .uploaded exists at '{dot_uploaded_candidate}', using .uploaded")
            upload_root_str = str(dot_uploaded_candidate.resolve())
        else:
            logger.error(f"[PATH ERROR] upload_root must be .uploaded (with dot), got: '{upload_root_str}'. Expected path ending with '.uploaded'")
            # Create .uploaded if parent exists
            if parent_dir.exists():
                dot_uploaded = parent_dir / ".uploaded"
                dot_uploaded.mkdir(exist_ok=True)
                logger.info(f"[PATH FIX] Created .uploaded directory at {dot_uploaded}")
                upload_root_str = str(dot_uploaded.resolve())
    
    _validate_upload_root(upload_root_str)
    workspaces_root = _get_workspaces_root(upload_root_str)
    dataset_slug = _slug(callback_state.get("original_dataset_name", "uploaded"), "uploaded")
    # Stable run id for the session (first time = create and store)
    run_id = callback_state.get("workspace_run_id")
    if not run_id:
        run_id = time.strftime("%Y%m%d_%H%M%S")
        callback_state["workspace_run_id"] = run_id

    ws = workspaces_root / dataset_slug / run_id
    subdirs = [
        "uploads", "data", "models", "reports", "results",
        "plots", "metrics", "indexes", "logs", "tmp", "manifests", "unstructured"
    ]
    logger.info(f"[ARTIFACT] Creating workspace structure: {ws}")
    for sd in subdirs:
        subdir_path = ws / sd
        subdir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"[ARTIFACT] Created/verified workspace folder: {subdir_path}")
    logger.info(f"[ARTIFACT] ✅ Workspace structure created with {len(subdirs)} folders for dataset '{dataset_slug}' (run: {run_id})")

    # Convenience pointers
    callback_state["workspace_root"] = str(ws)
    callback_state["workspace_paths"] = {sd: str(ws / sd) for sd in subdirs}
    # Update "latest" symlink for the dataset
    latest = workspaces_root / dataset_slug / "latest"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(ws, target_is_directory=True)
    except Exception as e:
        logger.debug(f"Could not update 'latest' symlink: {e}")

    return ws


def _try_recover_workspace_state(callback_state: Dict[str, Any]) -> bool:
    """
    Attempt to recover workspace_root and workspace_paths from disk if missing from state.
    Returns True if recovery successful, False otherwise.
    """
    if not callback_state:
        return False
    
    # Already have workspace_root? Just rebuild paths if needed
    workspace_root = callback_state.get("workspace_root")
    if workspace_root and os.path.exists(workspace_root):
        if not callback_state.get("workspace_paths"):
            logger.warning(f"[RECOVERY] Rebuilding workspace_paths from workspace_root: {workspace_root}")
            subdirs = ["uploads", "data", "plots", "reports", "results", "models", "tmp", "derived", 
                      "unstructured", "metrics", "indexes", "manifests"]
            ws = Path(workspace_root)
            callback_state["workspace_paths"] = {sd: str(ws / sd) for sd in subdirs}
            logger.info(f"[RECOVERY] [OK] Rebuilt workspace_paths")
        return True
    
    # Try to find latest workspace on disk
    try:
        from glob import glob
        try:
            from .large_data_config import UPLOAD_ROOT as _UPLOAD_ROOT
        except ImportError:
            _UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", ".uploads")
        
        workspace_pattern = os.path.join(str(_UPLOAD_ROOT), "_workspaces", "*", "*")
        workspaces = glob(workspace_pattern)
        
        if workspaces:
            latest_workspace = max(workspaces, key=os.path.getmtime)
            logger.warning(f"[RECOVERY] Found latest workspace on disk: {latest_workspace}")
            
            ws = Path(latest_workspace)
            subdirs = ["uploads", "data", "plots", "reports", "models", "tmp", "derived",
                      "unstructured", "metrics", "indexes", "manifests"]
            
            callback_state["workspace_root"] = str(ws)
            callback_state["workspace_paths"] = {sd: str(ws / sd) for sd in subdirs}
            
            # Try to find default CSV in this workspace
            uploads_dir = ws / "uploads"
            if uploads_dir.exists():
                csv_files = list(uploads_dir.glob("*.csv")) + list(uploads_dir.glob("*.parquet"))
                if csv_files:
                    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
                    callback_state["default_csv_path"] = str(latest_csv)
                    callback_state["dataset_csv_path"] = str(latest_csv)
                    callback_state["force_default_csv"] = True
                    logger.info(f"[RECOVERY] [OK] Bound to CSV: {latest_csv.name}")
            
            logger.info(f"[RECOVERY] [OK] Fully recovered workspace state from disk")
            return True
    except Exception as e:
        logger.error(f"[RECOVERY] Failed to recover workspace from disk: {e}")
    
    return False


def get_workspace_subdir(callback_state: Dict[str, Any], kind: str) -> Path:
    # Try to recover workspace state if missing
    if not callback_state.get("workspace_root") or not callback_state.get("workspace_paths"):
        logger.warning(f"[get_workspace_subdir] workspace state missing, attempting recovery...")
        _try_recover_workspace_state(callback_state)
    
    ws_root = Path(callback_state.get("workspace_root", "."))
    mapping = {
        "upload": "uploads",
        "data": "data",
        "model": "models",
        "models": "models",
        "report": "reports",
        "reports": "reports",
        "plot": "plots",
        "image": "plots",
        "metrics": "metrics",
        "index": "indexes",
        "log": "logs",
        "tmp": "tmp",
        "manifest": "manifests",
        "other": "data",
    }
    sub = mapping.get(kind.lower(), "data")
    p = ws_root / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def _current_dataset(state: Dict[str, Any]) -> str:
    """Extract dataset name from workspace_root path"""
    root = Path(state.get("workspace_root", ""))
    return root.parent.name if root and root.parent else "default"


def _sha256(p: Path, buf_size: int = 1024 * 1024) -> str:
    """Calculate SHA256 hash of a file"""
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            while True:
                b = f.read(buf_size)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except Exception as e:
        logger.warning(f"Failed to calculate hash for {p}: {e}")
        return ""


def _unique_path(dst_dir: Path, name: str) -> Path:
    """Generate unique path to avoid collisions"""
    base, ext = os.path.splitext(name)
    candidate = dst_dir / name
    i = 1
    while candidate.exists():
        candidate = dst_dir / f"{base}_{i}{ext}"
        i += 1
    return candidate


def _atomic_copy(src: Path, dst_dir: Path) -> Path:
    """
    Atomic copy using temp file + rename.
    [FIX] Checks if file already exists with same content to avoid numbered duplicates.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # [FIX] Check if exact same file already exists in destination
    # If so, return the existing path instead of creating a numbered duplicate
    candidate = dst_dir / src.name
    if candidate.exists():
        # Compare file hashes to check if they're identical
        src_hash = _sha256(src)
        dst_hash = _sha256(candidate)
        if src_hash and dst_hash and src_hash == dst_hash:
            logger.info(f"[ARTIFACT] File already exists with same content, skipping copy: {candidate.name}")
            return candidate
        else:
            logger.info(f"[ARTIFACT] File exists but content differs, creating new version")
    
    # Original logic: create unique path if needed
    dst = _unique_path(dst_dir, src.name)
    with tempfile.NamedTemporaryFile(dir=str(dst_dir), delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        shutil.copy2(str(src), str(tmp_path))
        os.replace(str(tmp_path), str(dst))  # atomic on same filesystem
        logger.info(f"[ARTIFACT] Copied file: {src.name} → {dst.name}")
        return dst
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _as_iter(obj: Any) -> Iterable[str]:
    """Convert object to iterable of strings, filtering empties"""
    if obj is None:
        return []
    if isinstance(obj, (list, tuple, set)):
        return [str(x) for x in obj if x]
    return [str(obj)] if obj else []


def _copy_or_move(src: Path, dst_dir: Path) -> Optional[Path]:
    """Copy or move file atomically with collision handling"""
    try:
        verbose_print = os.getenv("ARTIFACTS_VERBOSE_PRINT", "1") == "1"
        
        if _ARTIFACT_ROUTING_MODE == "move":
            dst = _atomic_copy(src, dst_dir)
            try:
                src.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to remove source after copy: {src}, {e}")
            if verbose_print:
                print(f" Artifact moved: {src.name} → {dst_dir.name}/")
            logger.info(f"Artifact moved: {src} → {dst}")
            return dst
        else:
            dst = _atomic_copy(src, dst_dir)
            if verbose_print:
                print(f" Artifact copied: {src.name} → {dst_dir.name}/")
            logger.info(f"Artifact copied: {src} → {dst}")
            return dst
    except Exception as e:
        logger.warning(f"Artifact copy/move failed for {src}: {e}")
        return None


def _manifest_path(callback_state: Dict[str, Any]) -> Path:
    """Generate unique manifest path with microsecond precision"""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return Path(callback_state["workspace_root"]) / "manifests" / f"manifest_{ts}.json"


def _collect_artifact_candidates(result: Any) -> Iterable[Dict[str, str]]:
    """
    Heuristics:
      - Prefer explicit `artifacts: [{path, type, label}]`
      - Else look for common keys: model_path(s), report_path(s), pdf_path, plot_paths, image_paths, metrics_path(s)
      - Else if `artifacts_dir` provided, ingest all files under it
    """
    if not isinstance(result, dict):
        return []

    out: list[Dict[str, str]] = []

    # 1) Explicit list
    for item in _as_iter(result.get("artifacts")):
        if isinstance(item, dict) and "path" in item:
            out.append({
                "path": str(item["path"]),
                "type": str(item.get("type", "other")),
                "label": str(item.get("label", "")),
            })

    # 2) Common single/multi keys
    key_map = {
        "model_path": "model",
        "model_paths": "model",
        "report_path": "report",
        "report_paths": "report",
        "pdf_path": "report",
        "plot_path": "plot",
        "plot_paths": "plot",
        "image_paths": "plot",
        "metrics_path": "metrics",
        "metrics_paths": "metrics",
        "index_path": "index",
    }
    for k, kind in key_map.items():
        val = result.get(k)
        for p in _as_iter(val):
            if p:
                out.append({"path": str(p), "type": kind, "label": k})

    # 3) Whole directory ingestion (with safety limits)
    artifacts_dir = result.get("artifacts_dir")
    max_bytes = int(os.getenv("ARTIFACTS_MAX_BYTES", "52428800"))  # 50MB default
    allowed_exts = set(e.strip().lower() for e in os.getenv("ARTIFACTS_ALLOWED_EXTS", "").split(",") if e.strip())
    
    if artifacts_dir and Path(artifacts_dir).exists():
        p = Path(artifacts_dir)
        if p.is_dir():
            for fp in p.rglob("*"):
                # Skip non-files and symlinks
                if not fp.is_file() or fp.is_symlink():
                    continue
                # Skip files with disallowed extensions (if filter is set)
                if allowed_exts and fp.suffix.lower() not in allowed_exts:
                    continue
                # Skip files exceeding size limit
                try:
                    if fp.stat().st_size > max_bytes:
                        logger.warning(f"Skipping large artifact: {fp} ({fp.stat().st_size} bytes)")
                        continue
                except Exception:
                    continue
                out.append({"path": str(fp), "type": "other", "label": "artifacts_dir"})

    return out


def route_artifacts_from_result(callback_state: Dict[str, Any], result: Any, tool_name: str) -> None:
    """
    Routes artifacts referenced by `result` into the workspace subfolders.
    Writes a manifest JSON for traceability.
    """
    # Enhanced logging
    logger.info(f"[ARTIFACT] Starting artifact routing for tool '{tool_name}'")
    logger.info(f"[artifact routing] Called for tool: {tool_name}")
    logger.info(f"[artifact routing] Result type: {type(result)}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    
    if not callback_state or "workspace_root" not in callback_state:
        logger.warning(f"[artifact routing] workspace_root missing, attempting recovery...")
        if not _try_recover_workspace_state(callback_state):
            # ADK State object may not support .keys()
            state_info = "None"
            if callback_state:
                try:
                    ws_root = callback_state.get('workspace_root', 'NOT_SET')
                    state_info = f"workspace_root={ws_root}"
                except Exception:
                    state_info = "state access failed"
            logger.warning(f"[artifact routing] Skipped - could not recover workspace ({state_info})")
            return

    moved: list[Dict[str, str]] = []
    candidates = _collect_artifact_candidates(result)
    logger.info(f"[ARTIFACT] Found {len(candidates)} artifact candidate(s) for routing")
    logger.info(f"[artifact routing] Found {len(candidates)} artifact candidates: {[c.get('path') for c in candidates]}")
    
    for item in candidates:
        src = Path(item["path"]).resolve()
        if not src.exists() or not src.is_file():
            logger.warning(f"[ARTIFACT] ⚠ Skipped non-existent file: {src}")
            logger.warning(f"[artifact routing] Skipped non-existent file: {src}")
            continue
        subdir = get_workspace_subdir(callback_state, item.get("type", "other"))
        logger.info(f"[ARTIFACT] Routing artifact '{src.name}' to folder '{subdir}' (type: {item.get('type', 'other')})")
        logger.info(f"[artifact routing] Copying {src.name} to {subdir}")
        dst = _copy_or_move(src, subdir)
        if dst:
            file_size = os.path.getsize(dst) if dst.exists() else 0
            logger.info(f"[ARTIFACT] ✅ Routed artifact '{src.name}' to '{subdir}' ({file_size} bytes)")
            logger.info(f"[artifact routing] [OK] Successfully copied to: {dst}")
            # Enhanced manifest with checksums, filesize, dataset, run_id
            workspace_root = Path(callback_state["workspace_root"])
            dataset_name = workspace_root.parent.name
            run_id = workspace_root.name
            
            moved.append({
                "tool": tool_name,
                "type": item.get("type", "other"),
                "label": item.get("label", ""),
                "src": str(src),
                "dst": str(dst),
                "filesize": os.path.getsize(dst),
                "sha256": _sha256(dst),
                "mode": _ARTIFACT_ROUTING_MODE,
                "dataset": dataset_name,
                "run_id": run_id,
                "ts": datetime.utcnow().isoformat() + "Z",
            })
        else:
            logger.warning(f"[artifact routing] Failed to copy: {src}")

    if moved:
        # Print summary
        workspace_root = Path(callback_state["workspace_root"])
        dataset_name = workspace_root.parent.name
        run_id = workspace_root.name
        print(f"[OK] Routed {len(moved)} artifact(s) to workspace: {dataset_name}/{run_id}/")
        
        try:
            man = _manifest_path(callback_state)
            man.parent.mkdir(parents=True, exist_ok=True)
            with man.open("w", encoding="utf-8") as f:
                json.dump(moved, f, indent=2)
            logger.info(f"Manifest written: {man}")
        except Exception as e:
            logger.debug(f"Could not write manifest: {e}")


# --- Session rehydration & explicit register+sync helpers ---

# [FIX #22-7] Idempotent guard for artifact operations
def ensure_artifact_fallbacks(state: Dict[str, Any]) -> None:
    """
    Idempotent guard: ensures workspace exists and session is rehydrated
    so artifact routing and listing never start from an invalid state.
    
    Call this at the start of tool wrappers (alongside ensure_file_bound).
    """
    try:
        rehydrate_session_state(state)
        if "workspace_root" not in state or not os.path.isdir(state.get("workspace_root", "")):
            ensure_workspace(state, _safe_get_upload_root())
    except Exception as e:
        logger.debug(f"ensure_artifact_fallbacks: {e}")


def _cleanup_duplicate_files_keep_oldest(uploads_dir: Path) -> None:
    """
    [CRITICAL] Remove duplicate files in uploads/ folder, keeping only the OLDEST file.
    
    Groups files by size (same size = likely duplicates), then keeps the file with
    the earliest modification time and deletes all others.
    
    This ensures all tools use only ONE file (the earliest one).
    """
    if not uploads_dir.exists():
        return
    
    try:
        from collections import defaultdict
        all_csvs = list(uploads_dir.glob("*.csv"))
        
        if len(all_csvs) <= 1:
            return  # No duplicates possible
        
        # Group files by size
        files_by_size = defaultdict(list)
        for csv_file in all_csvs:
            try:
                size = csv_file.stat().st_size
                files_by_size[size].append(csv_file)
            except Exception:
                continue
        
        # For each size group with multiple files, keep only oldest
        total_deleted = 0
        for size, files_list in files_by_size.items():
            if len(files_list) > 1:
                # Sort by modification time (oldest first)
                files_list.sort(key=lambda f: f.stat().st_mtime)
                oldest = files_list[0]
                
                # Delete all duplicates except oldest
                for duplicate in files_list[1:]:
                    try:
                        duplicate.unlink()
                        total_deleted += 1
                        logger.info(f"[CLEANUP] ✅ Deleted duplicate: {duplicate.name} (kept oldest: {oldest.name})")
                    except Exception as e:
                        logger.warning(f"[CLEANUP] Could not delete duplicate {duplicate.name}: {e}")
                
                if total_deleted > 0:
                    logger.info(f"[CLEANUP] ✅ Kept oldest file for size {size} bytes: {oldest.name}")
        
        if total_deleted > 0:
            logger.info(f"[CLEANUP] ✅✅✅ Cleaned up {total_deleted} duplicate file(s) from uploads/, kept oldest only")
            print(f"✅ Cleaned up {total_deleted} duplicate file(s), kept oldest only")
    except Exception as e:
        logger.warning(f"[CLEANUP] Error during duplicate cleanup: {e}")


def rehydrate_session_state(state: Dict[str, Any]) -> None:
    """
    Ensure critical state keys exist, rebuild workspace if missing, and bind the
    latest CSV/Parquet if current pointers are stale. Idempotent and safe.
    
    [NEW] Also cleans up duplicate files in uploads/ folder, keeping only the oldest.
    
    Also restores workflow state to continue from last step after server restart.
    """
    if not isinstance(state, dict):
        return

    try:
        # Late import to avoid circulars at import time
        from .large_data_config import UPLOAD_ROOT as _UPLOAD_ROOT
    except Exception:
        _UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", ".uploads")

    # Ensure workspace exists (dataset slug may be set later if needed)
    try:
        if not state.get("workspace_root"):
            ensure_workspace(state, _UPLOAD_ROOT)
    except Exception:
        # Do not fail hard; continue to attempt path binding
        pass

    # [FIX #22] Idempotent guard function
    ensure_artifact_fallbacks(state)
    
    # ===== WORKFLOW STATE PERSISTENCE =====
    # Restore workflow stage if not present (from persistent session storage)
    # This ensures workflow continues from last step after server restart
    if "workflow_stage" not in state or state.get("workflow_stage") is None:
        # Default to stage 1 if no saved state, but log it
        state["workflow_stage"] = 1
        state["last_workflow_action"] = "initialized"
        logger.info("[WORKFLOW] No saved workflow state found - starting at Stage 1")
    else:
        # Workflow state was restored from persistent storage
        saved_stage = state.get("workflow_stage")
        last_action = state.get("last_workflow_action", "unknown")
        logger.debug(f"[WORKFLOW] ✅ Restored workflow state: Stage {saved_stage} (last action: {last_action})")
    
    # Ensure workflow metadata exists
    if "workflow_started_at" not in state:
        from datetime import datetime
        state["workflow_started_at"] = datetime.now().isoformat()
    
    if "workflow_updated_at" not in state:
        from datetime import datetime
        state["workflow_updated_at"] = datetime.now().isoformat()
    
    # Prefer previously bound CSV
    csv_path = state.get("default_csv_path") or state.get("dataset_csv_path")

    # [CRITICAL FIX] Only auto-discover if NO file is currently bound
    # This prevents processing old files from previous sessions
    if csv_path and os.path.exists(csv_path):
        # File already bound and exists - skip auto-discovery
        logger.debug(f"[AUTO-DISCOVERY] Skipping search - file already bound: {csv_path}")
    else:
        # If missing or not on disk, discover freshest on disk under UPLOAD_ROOT
        def _latest(patterns):
            from glob import glob
            candidates: list[str] = []
            # [FIX #20-4 + #21] Search multiple locations including .uploaded and uploads subdirectories
            # [CRITICAL FIX] Use NON-RECURSIVE search to avoid finding old workspace files
            likely_roots = [
                _UPLOAD_ROOT,
                os.path.join(_UPLOAD_ROOT, ".uploaded"),  # Hidden upload directory (top-level only)
                os.path.join(_UPLOAD_ROOT, "uploads")      # Standard uploads directory (top-level only)
            ]
            for root in dict.fromkeys([p for p in likely_roots if p]):  # unique, non-empty
                if os.path.isdir(root):
                    for pat in patterns:
                        # NON-RECURSIVE: Only search immediate directory, not subdirectories
                        candidates += glob(os.path.join(root, pat), recursive=False)
            if not candidates:
                return None
            try:
                return max(candidates, key=os.path.getmtime)
            except Exception:
                return candidates[-1] if candidates else None

        candidate = _latest(["*.csv", "*.parquet"])
        if candidate:
            state["default_csv_path"] = candidate
            state["dataset_csv_path"] = candidate
            state["force_default_csv"] = True
            logger.info(f"[AUTO-DISCOVERY] Found and bound: {candidate}")

    # [CRITICAL FIX] REMOVED auto-copy logic that was causing infinite file duplication
    # Files are already copied during upload in agent.py (_handle_file_uploads_callback)
    # This redundant copy was creating new timestamped files on EVERY tool call!
    # 
    # Original problem: rehydrate_session_state runs on every tool call
    # → Tries to copy file to uploads/
    # → Creates new timestamp-prefixed filename
    # → New filename doesn't exist, so copies again
    # → Result: 11+ duplicate files!
    #
    # Solution: Remove this block entirely - files are already in the right place


def register_and_sync_artifact(callback_context, path: str, kind: str, label: str) -> None:
    """
    Register the artifact in our registry AND mirror it to the ADK artifact panel.
    Safe to call repeatedly. Best-effort; never raises.
    """
    logger.info(f"[ARTIFACT SYNC] Starting registration for: {path}")
    logger.info(f"[ARTIFACT SYNC] Kind: {kind}, Label: {label}")
    logger.info(f"[ARTIFACT SYNC] File exists: {os.path.exists(path)}")
    
    # 1) Register in our registry/workspace
    try:
        state = getattr(callback_context, "state", {})
        # ADK State object is dict-like but may not have .keys() method
        try:
            state_info = f"workspace_root={state.get('workspace_root')}"
        except Exception:
            state_info = "state access failed"
        logger.info(f"[ARTIFACT SYNC] State info: {state_info}")
        
        register_artifact(state, path, kind=kind, label=label)
        logger.info(f"[ARTIFACT SYNC] [OK] Successfully registered in workspace")
    except Exception as e:
        logger.warning(f"[ARTIFACT SYNC] [X] Register failed for {path}: {e}")
        logger.exception("Full registration error:")

    # 2) Mirror to ADK panel if available
    try:
        if callback_context and hasattr(callback_context, "save_artifact"):
            logger.info(f"[ARTIFACT SYNC] Mirroring to ADK panel...")
            from google.genai import types as _types
            import mimetypes as _mimetypes
            
            if not os.path.exists(path):
                logger.warning(f"[ARTIFACT SYNC] [X] File not found for mirroring: {path}")
                return
                
            file_size = os.path.getsize(path)
            logger.info(f"[ARTIFACT SYNC] File size: {file_size} bytes")

            # Detect correct MIME type (images, pdf, json, csv, parquet, etc.)
            fname = os.path.basename(path)
            detected, _ = _mimetypes.guess_type(fname)
            mime_type = detected or "application/octet-stream"
            # Parquet is often None; set explicitly
            if fname.lower().endswith(".parquet"):
                mime_type = "application/octet-stream"
            
            with open(path, "rb") as fh:
                blob = _types.Blob(data=fh.read(), mime_type=mime_type)
            part = _types.Part(inline_data=blob)

            import asyncio as _asyncio
            try:
                loop = _asyncio.get_running_loop()
                loop.create_task(callback_context.save_artifact(fname, part))
                logger.info(f"[ARTIFACT SYNC] [OK] Mirrored to ADK panel (async) as {mime_type}")
            except RuntimeError:
                _asyncio.run(callback_context.save_artifact(fname, part))
                logger.info(f"[ARTIFACT SYNC] [OK] Mirrored to ADK panel (sync) as {mime_type}")
        else:
            logger.warning(f"[ARTIFACT SYNC] [WARNING] No save_artifact method available")
    except Exception as e:
        logger.warning(f"[ARTIFACT SYNC] [X] save_artifact mirror failed for {path}: {e}")
        logger.exception("Full mirror error:")

# --- Optional: expose a function-tool friendly helper
def register_artifact(callback_state: Dict[str, Any], path: str, kind: str = "other", label: str = "") -> Dict[str, str]:
    """
    Tools may call this directly to stash any file into the workspace with a declared kind.
    Enhanced with dataset-scoped versioning and latest tracking.
    """
    if not callback_state or "workspace_root" not in callback_state:
        logger.warning("[register_artifact] workspace_root missing, attempting recovery...")
        if not _try_recover_workspace_state(callback_state):
            raise RuntimeError("Workspace not initialized and could not be recovered from disk")
    src = Path(path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Artifact not found: {src}")
    dst = _copy_or_move(src, get_workspace_subdir(callback_state, kind))
    
    # Dataset-scoped version tracking
    dataset = _current_dataset(callback_state)
    ver = 0
    if label:
        _VERSIONS_BY_LABEL[dataset][label] += 1
        ver = _VERSIONS_BY_LABEL[dataset][label]
        _LATEST_BY_LABEL[dataset][label] = {"path": str(dst) if dst else str(src), "version": ver}
    
    rec = {
        "path": str(dst) if dst else str(src), 
        "kind": kind, 
        "label": label, 
        "version": ver,
        "dataset": dataset,
        "created_at": datetime.utcnow().isoformat()+"Z"
    }
    _ARTIFACTS.append(rec)
    
    try:
        st = callback_state.get("artifacts") or []
        st.append(rec)
        callback_state["artifacts"] = st
    except Exception:
        pass
    
    return {"status": "success", "kind": kind, "src": str(src), "dst": str(dst) if dst else "", "version": ver}

def resolve_latest(label: str, *, dataset: str | None = None, state: Dict[str, Any] | None = None) -> str:
    """Return latest path for a logical artifact label, scoped by dataset."""
    if dataset is None and state:
        dataset = _current_dataset(state)
    ds = dataset or "default"
    info = _LATEST_BY_LABEL.get(ds, {}).get(label)
    return info["path"] if info else ""

def list_artifacts(label: str = "", kind: str = "", dataset: str = "") -> list[Dict[str, Any]]:
    """List artifacts with optional filters for label, kind, and dataset."""
    result = list(_ARTIFACTS)
    if label:
        result = [a for a in result if a.get("label") == label]
    if kind:
        result = [a for a in result if a.get("kind") == kind]
    if dataset:
        result = [a for a in result if a.get("dataset") == dataset]
    return result


def make_artifact_routing_wrapper(tool_name: str, wrapped_func):
    """
    Wrap a tool function so that after it returns, we attempt to route artifacts
    based on its return payload (non-invasive; no changes to tool code).
    Assumes first arg is a context object with a `.state` dict.
    """
    import asyncio
    import inspect
    from functools import wraps
    
    # Check if the wrapped function is async
    is_async = asyncio.iscoroutinefunction(wrapped_func)
    
    if is_async:
        @wraps(wrapped_func)
        async def _async_wrapper(*args, **kwargs):
            logger.debug(f"[artifact routing wrapper] Calling {tool_name}")
            result = await wrapped_func(*args, **kwargs)
            try:
                # Find a context-like object with .state
                ctx_like = None
                # Check kwargs first (most common for ADK tools)
                if "tool_context" in kwargs and hasattr(kwargs["tool_context"], "state"):
                    ctx_like = kwargs["tool_context"]
                    logger.debug(f"[artifact routing wrapper] Found tool_context in kwargs")
                # Fall back to args[0]
                elif args and hasattr(args[0], "state"):
                    ctx_like = args[0]
                    logger.debug(f"[artifact routing wrapper] Found context in args[0]")
                
                if ctx_like and isinstance(getattr(ctx_like, "state", None), dict):
                    logger.debug(f"[artifact routing wrapper] Routing artifacts for {tool_name}")
                    route_artifacts_from_result(ctx_like.state, result, tool_name)
                else:
                    logger.debug(f"[artifact routing wrapper] No valid context found for {tool_name}")
            except Exception as e:
                logger.warning(f"[artifact routing] {tool_name} post-hook error: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            return result
        # Mark as artifact-routing-wrapped to prevent double wrapping
        _async_wrapper._artifact_routing_applied = True
        return _async_wrapper
    else:
        @wraps(wrapped_func)
        def _sync_wrapper(*args, **kwargs):
            result = wrapped_func(*args, **kwargs)
            try:
                # Find a context-like object with .state
                ctx_like = None
                # Check kwargs first (most common for ADK tools)
                if "tool_context" in kwargs and hasattr(kwargs["tool_context"], "state"):
                    ctx_like = kwargs["tool_context"]
                # Fall back to args[0]
                elif args and hasattr(args[0], "state"):
                    ctx_like = args[0]
                
                if ctx_like and isinstance(getattr(ctx_like, "state", None), dict):
                    route_artifacts_from_result(ctx_like.state, result, tool_name)
            except Exception as e:
                logger.debug(f"[artifact routing] {tool_name} post-hook error: {e}")
            return result
        # Mark as artifact-routing-wrapped to prevent double wrapping
        _sync_wrapper._artifact_routing_applied = True
        return _sync_wrapper


def get_workspace_info(callback_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns the current workspace structure for UI/debugging.
    """
    root = callback_state.get("workspace_root", "")
    paths = callback_state.get("workspace_paths", {})
    return {"workspace_root": root, "subdirs": paths}

