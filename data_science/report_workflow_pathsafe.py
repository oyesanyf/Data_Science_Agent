import os
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from google.adk.agents.callback_context import CallbackContext

from data_science import artifact_manager as artifact_manager
from .executive_report_guard import export_executive_report_tool_guard
from .ds_tools import export as export_technical_report

logger = logging.getLogger(__name__)

_TS_DIR_RE = re.compile(r"^\d{8}_\d{6}$")  # 20251021_124423

def _slug(s: Optional[str], default: str = "dataset") -> str:
    s = (s or default).strip()
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or default

def _nowtag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _is_ts_dir(p: Path) -> bool:
    return p.is_dir() and _TS_DIR_RE.match(p.name or "") is not None

def _nearest_dataset_root_from_workspace_root(workspace_root: Path) -> Optional[Path]:
    if not workspace_root:
        return None
    p = workspace_root
    if _is_ts_dir(p):
        return p.parent
    try:
        has_ts_child = any(_is_ts_dir(c) for c in p.iterdir() if c.is_dir())
    except Exception:
        has_ts_child = False
    if has_ts_child:
        return p
    for ancestor in p.parents:
        if _is_ts_dir(ancestor):
            return ancestor.parent
    return None

def _nearest_dataset_root_from_hint(path_hint: Path) -> Optional[Path]:
    if not path_hint:
        return None
    p = path_hint if path_hint.exists() else path_hint.parent
    for ancestor in [p, *p.parents]:
        if _is_ts_dir(ancestor):
            return ancestor.parent
    return None

def _guess_dataset_root(ctx: CallbackContext) -> Optional[Path]:
    state = getattr(ctx, "state", {}) or {}
    ws = state.get("workspace_root")
    if ws:
        root = _nearest_dataset_root_from_workspace_root(Path(ws))
        if root and root.exists():
            return root
    csvp = state.get("default_csv_path")
    if csvp:
        root = _nearest_dataset_root_from_hint(Path(csvp))
        if root and root.exists():
            return root
    for v in state.values():
        try:
            if isinstance(v, str) and ("/" in v or "\\" in v):
                root = _nearest_dataset_root_from_hint(Path(v))
                if root and root.exists():
                    return root
        except Exception:
            pass
    try:
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.warning(f"[_guess_dataset_root] rehydrate failed: {e}")
        
        try:
            artifact_manager.ensure_workspace(state, None)
        except Exception as e:
            logger.warning(f"[_guess_dataset_root] ensure_workspace failed: {e}")
            # Try recovery
            from .artifact_manager import _try_recover_workspace_state
            if _try_recover_workspace_state(state):
                logger.info(f"[_guess_dataset_root] [OK] Workspace recovered from disk")
        
        ws = state.get("workspace_root")
        if ws:
            root = _nearest_dataset_root_from_workspace_root(Path(ws))
            if root and root.exists():
                return root
    except Exception as e:
        logger.error(f"[_guess_dataset_root] Recovery failed: {e}")
    return None

def _latest_run_dir(dataset_root: Path) -> Optional[Path]:
    try:
        ts_dirs = [c for c in dataset_root.iterdir() if _is_ts_dir(c)]
        if not ts_dirs:
            return None
        ts_dirs.sort(key=lambda p: p.name, reverse=True)
        return ts_dirs[0]
    except Exception as e:
        logger.warning(f"[reports] listing runs under {dataset_root}: {e}")
        return None

def _merge_pdfs_safe(out_path: Path, inputs: List[Path]) -> bool:
    try:
        from PyPDF2 import PdfMerger
    except Exception as e:
        logger.info(f"[reports] PyPDF2 not available, skip merge: {e}")
        return False
    try:
        merger = PdfMerger()
        count = 0
        for p in inputs:
            if p and p.exists() and p.is_file():
                merger.append(str(p))
                count += 1
        if count == 0:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            merger.write(f)
        merger.close()
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        logger.warning(f"[reports] PDF merge failed: {e}")
        return False

def _safe_copy(src: Optional[Path], dst: Path) -> Optional[Path]:
    try:
        if src and src.exists() and src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return dst if dst.exists() else None
    except Exception as e:
        logger.warning(f"[reports] copy failed {src} -> {dst}: {e}")
    return None

def _register(ctx: CallbackContext, path: Optional[Path], kind: str, label: str) -> Optional[str]:
    if not path or not path.exists() or not path.is_file():
        return None
    try:
        state = getattr(ctx, "state", {})
        artifact_manager.register_artifact(state, str(path), kind=kind, label=label)
        # Also mirror to ADK panel for visibility
        artifact_manager.register_and_sync_artifact(ctx, str(path), kind=kind, label=label)
    except Exception as e:
        logger.warning(f"[reports] register_artifact failed for {path}: {e}")
    return str(path)

def export_reports_for_latest_run_pathsafe(
    tool_context: CallbackContext,
    title: str = "Executive Report",
    notes: str = "",
    include_technical_appendix: bool = True,
) -> dict:
    state = getattr(tool_context, "state", {}) or {}
    dataset_name = _slug(state.get("original_dataset_name"), "dataset")

    dataset_root = _guess_dataset_root(tool_context)
    if not dataset_root:
        return {
            "status": "partial",
            "message": "Could not infer dataset root from context; ensure workspace_root or default_csv_path is present in state.",
            "files": {},
            "extra": {"dataset": dataset_name}
        }

    run_root = _latest_run_dir(dataset_root)
    if not run_root:
        return {
            "status": "partial",
            "message": f"No timestamped run folder under {dataset_root}. Create a run first.",
            "files": {},
            "extra": {"dataset": dataset_name, "dataset_root": str(dataset_root)}
        }

    reports_dir = run_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    latest_dir = dataset_root / "_workdlow" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    ts = _nowtag()
    exec_pdf_run   = reports_dir / f"{dataset_name}_executive_{ts}.pdf"
    tech_pdf_run   = reports_dir / f"{dataset_name}_technical_{ts}.pdf"
    comb_pdf_run   = reports_dir / f"{dataset_name}_EXECUTIVE_COMBINED_{ts}.pdf"

    exec_pdf_latest = latest_dir / exec_pdf_run.name
    tech_pdf_latest = latest_dir / tech_pdf_run.name
    comb_pdf_latest = latest_dir / comb_pdf_run.name

    executive_pdf_path: Optional[Path] = None
    try:
        res = export_executive_report_tool_guard(
            tool_context=tool_context,
            title=title,
            notes=notes,
        )
        if isinstance(res, dict) and res.get("status") == "success":
            src = res.get("pdf_path") or res.get("file") or res.get("path")
            if src:
                srcp = Path(src)
                executive_pdf_path = _safe_copy(srcp, exec_pdf_run) or srcp
                _safe_copy(executive_pdf_path, exec_pdf_latest)
                _register(tool_context, executive_pdf_path, "report", "executive_report")
        else:
            logger.warning(f"[reports] executive guard non-success: {res}")
    except Exception as e:
        logger.error(f"[reports] executive export failed: {e}", exc_info=True)

    technical_pdf_path: Optional[Path] = None
    if include_technical_appendix:
        try:
            t_res = export_technical_report(
                title=f"{title} — Technical Appendix",
                tool_context=tool_context
            )
            if isinstance(t_res, dict) and t_res.get("status") == "success":
                src = t_res.get("pdf_path") or t_res.get("file") or t_res.get("path")
                if src:
                    srcp = Path(src)
                    technical_pdf_path = _safe_copy(srcp, tech_pdf_run) or srcp
                    _safe_copy(technical_pdf_path, tech_pdf_latest)
                    _register(tool_context, technical_pdf_path, "report", "technical_report")
            else:
                logger.warning(f"[reports] technical export non-success: {t_res}")
        except Exception as e:
            logger.error(f"[reports] technical export failed: {e}", exc_info=True)

    combined_ok = False
    if executive_pdf_path and executive_pdf_path.exists():
        inputs = [executive_pdf_path]
        if include_technical_appendix and technical_pdf_path and technical_pdf_path.exists():
            inputs.append(technical_pdf_path)
        if len(inputs) > 1:
            combined_ok = _merge_pdfs_safe(comb_pdf_run, inputs)
            if combined_ok:
                _safe_copy(comb_pdf_run, comb_pdf_latest)
                _register(tool_context, comb_pdf_run, "report", "executive_report_combined")

    files = {
        "run_reports_dir": str(reports_dir),
        "latest_dir": str(latest_dir),
        "executive_pdf_run": str(exec_pdf_run) if exec_pdf_run.exists() else None,
        "technical_pdf_run": str(tech_pdf_run) if tech_pdf_run.exists() else None,
        "combined_pdf_run": str(comb_pdf_run) if comb_pdf_run.exists() else None,
        "executive_pdf_latest": str(exec_pdf_latest) if exec_pdf_latest.exists() else None,
        "technical_pdf_latest": str(tech_pdf_latest) if tech_pdf_latest.exists() else None,
        "combined_pdf_latest": str(comb_pdf_latest) if comb_pdf_latest.exists() else None,
    }

    if files["combined_pdf_run"]:
        return {
            "status": "success",
            "message": "Executive + Technical generated in run/reports and mirrored to _workdlow\\latest.",
            "files": files,
            "extra": {"dataset": dataset_name, "dataset_root": str(dataset_root), "run_root": str(run_root)}
        }
    if files["executive_pdf_run"] or files["technical_pdf_run"]:
        return {
            "status": "partial",
            "message": "Individual PDFs generated. Merge skipped or unavailable (PyPDF2 optional).",
            "files": files,
            "extra": {"dataset": dataset_name, "dataset_root": str(dataset_root), "run_root": str(run_root)}
        }
    return {
        "status": "partial",
        "message": "No PDFs produced (exporters returned non-success), but workflow didn’t crash.",
        "files": files,
        "extra": {"dataset": dataset_name, "dataset_root": str(dataset_root), "run_root": str(run_root)}
    }


