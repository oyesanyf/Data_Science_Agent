# data_science/ui_page.py
from pathlib import Path
"""
Centralized UI page sink for Data Science Agent.
Creates individual markdown files for each tool execution, plus an index file.
"""
import os
import io
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from google.adk.agents.callback_context import CallbackContext

UI_FILENAME = "session_ui_page.md"  # Index file
# CRITICAL: Use 'reports/' folder (canonical structure) instead of 'tool_executions/'
UI_EXECUTIONS_DIR = "reports"  # Directory for individual tool files - follows canonical folder structure

def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _get_logger():
    """Get the shared 'tools' logger so messages appear in tools.log."""
    import logging
    try:
        # Prefer centralized tools logger if available
        from logging_config import get_tools_logger  # type: ignore
        return get_tools_logger()
    except Exception:
        # Fallback: use a logger named 'tools'
        logger = logging.getLogger("tools")
        if not logger.handlers:
            # Ensure at least a basic handler exists in ad-hoc contexts
            handler = logging.StreamHandler()
            logger.addHandler(handler)
        return logger

def _timestamp_ms() -> str:
    """Generate timestamp with microseconds to prevent collisions."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _state_as_dict(ctx: CallbackContext) -> Dict[str, Any]:
    """Normalize ctx.state access to always return a dict."""
    s = getattr(ctx, "state", {}) or {}
    if isinstance(s, dict):
        return s
    # Try best-effort conversion
    try:
        return dict(s)
    except Exception:
        return getattr(s, "__dict__", {}) or {}

def _relpath_posix(from_path: str, to_path: str) -> str:
    """Generate relative POSIX path for markdown links."""
    rel = os.path.relpath(to_path, start=os.path.dirname(from_path))
    return Path(rel).as_posix()

def _md_table_from_rows(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    out = []
    out.append("| " + " | ".join(header) + " |")
    out.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)

def clear_ui_page(ctx: CallbackContext) -> str:
    """Clear (reset) the UI page by deleting it - will be recreated on next ensure_ui_page call."""
    logger = _get_logger()
    
    _state = _state_as_dict(ctx)
    workspace_root = _state.get("workspace_root")
    
    if workspace_root:
        page_path = str(Path(workspace_root) / UI_FILENAME)
    else:
        ws = _state.get("workspace_paths", {})
        docs_dir = ws.get("reports") if isinstance(ws, dict) else ws.get("uploads") if hasattr(ws, 'get') else os.getcwd()
        if not docs_dir:
            docs_dir = os.getcwd()
        page_path = str(Path(docs_dir) / UI_FILENAME)
    
    if Path(page_path).exists():
        try:
            Path(page_path).unlink()
            logger.info(f"[UI SINK] Cleared UI page at: {page_path}")
        except Exception as e:
            logger.warning(f"[UI SINK] Failed to clear UI page: {e}")
    
    return page_path

def ensure_ui_page(ctx: CallbackContext, clear_existing: bool = False) -> str:
    """
    Ensure UI page exists and return its path.
    
    Args:
        ctx: Callback context
        clear_existing: If True, clear any existing page before creating new one (for fresh start)
    """
    logger = _get_logger()
    
    # Get workspace root from state (follows .uploaded/_workspaces/<dataset>/<timestamp>/ structure)
    _state = _state_as_dict(ctx)
    workspace_root = _state.get("workspace_root")
    
    # [CRITICAL FIX] If workspace_root is None, try to get it from workspace_paths or create it
    if not workspace_root:
        workspace_paths = _state.get("workspace_paths", {})
        if isinstance(workspace_paths, dict) and workspace_paths:
            # Try to derive workspace_root from workspace_paths
            reports_path = workspace_paths.get("reports") or workspace_paths.get("uploads")
            if reports_path:
                # workspace_paths[key] = workspace_root/key, so go up one level
                workspace_root = str(Path(reports_path).parent)
                logger.info(f"[UI SINK] Derived workspace_root from workspace_paths: {workspace_root}")
        
        # If still None, ensure workspace is created
        if not workspace_root:
            try:
                from . import artifact_manager
                from .large_data_config import UPLOAD_ROOT
                # This will set workspace_root in state
                artifact_manager.ensure_workspace(_state, UPLOAD_ROOT)
                workspace_root = _state.get("workspace_root")
                logger.info(f"[UI SINK] Created workspace_root via ensure_workspace: {workspace_root}")
            except Exception as e:
                logger.warning(f"[UI SINK] Failed to create workspace_root: {e}")
    
    logger.info(f"[UI SINK] ensure_ui_page called, workspace_root={workspace_root}, clear_existing={clear_existing}")
    
    if workspace_root:
        # Use workspace root directly (already points to .uploaded/_workspaces/<dataset>/<timestamp>/)
        page_path = str(Path(workspace_root) / UI_FILENAME)
        logger.info(f"[UI SINK] Using workspace_root path: {page_path}")
    else:
        # [CRITICAL] Try harder to get workspace_root before falling back
        # This should rarely happen if ensure_workspace is called properly
        ws = _state.get("workspace_paths", {})
        logger.warning(f"[UI SINK] No workspace_root! Attempting recovery from workspace_paths: {list(ws.keys()) if isinstance(ws, dict) else 'None'}")
        
        docs_dir = None
        if isinstance(ws, dict):
            docs_dir = ws.get("reports")
            if docs_dir:
                # Derive workspace_root from reports path
                workspace_root = str(Path(docs_dir).parent)
                page_path = str(Path(workspace_root) / UI_FILENAME)
                logger.info(f"[UI SINK] ✅ Recovered workspace_root from workspace_paths.reports: {workspace_root}")
            else:
                # Last resort fallback - should not happen in normal operation
                base = Path(__file__).parent / ".uploaded"
                docs_dir = str(base / "reports")
                page_path = str(Path(docs_dir) / UI_FILENAME)
                logger.error(f"[UI SINK] ❌ CRITICAL: Using fallback path (workspace not properly initialized): {page_path}")
        else:
            # Last resort fallback - should not happen in normal operation
            base = Path(__file__).parent / ".uploaded"
            docs_dir = str(base / "reports")
            page_path = str(Path(docs_dir) / UI_FILENAME)
            logger.error(f"[UI SINK] ❌ CRITICAL: Using fallback path (no workspace_paths available): {page_path}")
    
    # Do not write back to ctx.state; ToolContext.state may be read-only.
    
    # Clear existing if requested OR create file if missing
    if clear_existing and Path(page_path).exists():
        logger.info(f"[UI SINK] Clearing existing UI page at: {page_path}")
        try:
            Path(page_path).unlink()
        except Exception as e:
            logger.warning(f"[UI SINK] Failed to clear existing page: {e}")
    
    if not Path(page_path).exists():
        logger.info(f"[UI SINK] Creating new UI index page at: {page_path}")
        os.makedirs(Path(page_path).parent, exist_ok=True)
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(f"#  Data Science Agent - Session UI Index\n\n")
            f.write(f"**Session started:** {_now()}\n\n")
            f.write("---\n\n")
            f.write("This index links to individual tool execution files.\n")
            f.write(f"Each tool execution creates its own file in the `{UI_EXECUTIONS_DIR}/` directory.\n\n")
        logger.info(f"[UI SINK] [OK] UI index page created successfully")
    else:
        logger.info(f"[UI SINK] UI page already exists at: {page_path}")
    
    return page_path

def _append_markdown(page_path: str, markdown: str):
    """Append markdown content to the UI page."""
    with open(page_path, "a", encoding="utf-8") as f:
        f.write(markdown)
        if not markdown.endswith("\n"):
            f.write("\n")

def append_section(ctx: CallbackContext, title: str, body_md: str):
    """Append a markdown section to the UI page."""
    logger = _get_logger()
    
    page = ensure_ui_page(ctx)
    logger.info(f"[UI SINK] append_section: title='{title}', body_md length={len(body_md) if body_md else 0}")
    
    # If body_md is empty or very short, log a warning
    if not body_md or len(body_md.strip()) < 10:
        logger.warning(f"[UI SINK] ⚠️ append_section called with empty/short content! title='{title}', body_md='{body_md[:100] if body_md else 'None'}'")
    
    _append_markdown(page, f"\n\n## {title}\n\n{body_md}\n\n_Last updated {_now()}_")

def append_table(ctx: CallbackContext, title: str, rows: List[List[str]]):
    """Append a markdown table to the UI page."""
    page = ensure_ui_page(ctx)
    _append_markdown(page, f"\n\n## {title}\n\n{_md_table_from_rows(rows)}\n")

def append_artifact_list(ctx: CallbackContext, title: str, filenames: List[str]):
    """Append a list of artifact links to the UI page."""
    if not filenames:
        return
    bullets = "\n".join([f"- **{n}** *(see Artifacts)*" for n in filenames])
    append_section(ctx, title, bullets)

def _get_executions_dir(ctx: CallbackContext) -> Path:
    """Get or create the tool executions directory (reports/ folder) in the proper workspace."""
    logger = _get_logger()
    _state = _state_as_dict(ctx)
    workspace_root = _state.get("workspace_root")
    
    # [CRITICAL] Always try to get workspace_root - never fall back to .uploaded/reports
    if not workspace_root:
        # Try to derive from workspace_paths
        workspace_paths = _state.get("workspace_paths", {})
        if isinstance(workspace_paths, dict) and workspace_paths:
            reports_path = workspace_paths.get("reports")
            if reports_path:
                workspace_root = str(Path(reports_path).parent)
                logger.info(f"[UI SINK] Derived workspace_root from workspace_paths.reports: {workspace_root}")
        
        # If still None, ensure workspace is created
        if not workspace_root:
            try:
                from . import artifact_manager
                from .large_data_config import UPLOAD_ROOT
                # This will set workspace_root in state
                artifact_manager.ensure_workspace(_state, UPLOAD_ROOT)
                workspace_root = _state.get("workspace_root")
                logger.info(f"[UI SINK] Created workspace_root via ensure_workspace: {workspace_root}")
            except Exception as e:
                logger.error(f"[UI SINK] Failed to create workspace: {e}")
        
        # If still None, try to find the most recent workspace
        if not workspace_root:
            try:
                from .large_data_config import UPLOAD_ROOT
                from pathlib import Path
                workspaces_root = Path(UPLOAD_ROOT) / "_workspaces"
                if workspaces_root.exists():
                    # Find the most recently modified workspace (excluding default/_global)
                    recent_workspaces = [
                        d for d in workspaces_root.iterdir()
                        if d.is_dir() and d.name not in ("default", "_global")
                    ]
                    if recent_workspaces:
                        # Get most recent dataset folder
                        most_recent_dataset = max(recent_workspaces, key=lambda p: p.stat().st_mtime)
                        # Get most recent run_id subfolder
                        run_folders = [d for d in most_recent_dataset.iterdir() if d.is_dir()]
                        if run_folders:
                            latest_run = max(run_folders, key=lambda p: p.stat().st_mtime)
                            workspace_root = str(latest_run)
                            logger.info(f"[UI SINK] Inferred workspace_root from most recent workspace: {workspace_root}")
            except Exception as e:
                logger.error(f"[UI SINK] Failed to infer workspace: {e}")
    
    if workspace_root:
        # Use workspace_root/reports (canonical structure) - ALWAYS prefer this
        exec_dir = Path(workspace_root) / UI_EXECUTIONS_DIR
        logger.info(f"[UI SINK] Using workspace reports directory: {exec_dir}")
    else:
        # LAST RESORT: Log error but still create fallback (should rarely happen)
        logger.error(f"[UI SINK] ❌ CRITICAL: No workspace_root available! Using fallback path.")
        logger.error(f"[UI SINK] This should not happen - workspace should always be initialized.")
        base = Path(__file__).parent / ".uploaded"
        exec_dir = base / "reports"
    
    exec_dir.mkdir(parents=True, exist_ok=True)
    return exec_dir

def _create_tool_execution_file(ctx: CallbackContext, tool_name: str, blocks: List[Dict[str, Any]]) -> str:
    """Create an individual markdown file for this tool execution."""
    logger = _get_logger()
    
    exec_dir = _get_executions_dir(ctx)
    timestamp = _timestamp_ms()  # Includes microseconds to prevent collisions
    # Sanitize tool_name for filename
    safe_tool_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in tool_name)
    filename = f"{timestamp}_{safe_tool_name}.md"
    filepath = exec_dir / filename
    
    logger.info(f"[UI SINK] Creating individual tool execution file: {filepath}")
    logger.info(f"[UI SINK] Received {len(blocks)} blocks for {tool_name}")
    for i, b in enumerate(blocks):
        logger.info(f"[UI SINK] Block {i}: type={b.get('type')}, title={b.get('title')}, content_length={len(str(b.get('content', '')))}")
        logger.debug(f"[UI SINK] Block {i} content preview: {str(b.get('content', ''))[:200]}")
    
    # Build markdown content
    content_parts = []
    content_parts.append(f"# {tool_name}\n\n")
    content_parts.append(f"**Executed:** {_now()}\n\n")
    content_parts.append("---\n\n")
    
    for i, b in enumerate(blocks):
        t = (b.get("type") or "markdown").lower()
        title = b.get("title") or t.title()
        
        if t == "markdown":
            block_content = b.get("content", "")
            logger.info(f"[UI SINK] Processing markdown block {i}: title='{title}', content_length={len(str(block_content))}")
            if block_content:
                # CRITICAL: Ensure UTF-8 encoding is preserved when writing
                content_parts.append(f"## {title}\n\n{block_content}\n\n")
                logger.info(f"[UI SINK] ✅ Added markdown block {i} to content (length: {len(block_content)} chars)")
            else:
                logger.warning(f"[UI SINK] ⚠️ Markdown block {i} has empty content!")
        elif t == "table":
            rows = b.get("rows") or []
            if rows:
                content_parts.append(f"## {title}\n\n{_md_table_from_rows(rows)}\n\n")
        elif t == "artifact_list":
            files = b.get("files") or []
            if files:
                # Make artifact links clickable if possible
                bullets = "\n".join([f"- [{n}](./{n})" for n in files])
                content_parts.append(f"## {title}\n\n{bullets}\n\n")
        else:
            content_parts.append(f"## {title}\n\nUnsupported block type: `{t}`\n\n")
    
    # Write to file
    full_content = "".join(content_parts)
    logger.info(f"[UI SINK] Writing {len(full_content)} chars to {filepath}")
    logger.debug(f"[UI SINK] Content preview (first 500 chars): {full_content[:500]}")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    logger.info(f"[UI SINK] Created tool execution file: {filename} ({len(full_content)} chars written)")
    return str(filepath)

def _update_index_file(ctx: CallbackContext, tool_name: str, execution_file: str):
    """Update the index file that links to all tool executions."""
    logger = _get_logger()
    
    page = ensure_ui_page(ctx)
    timestamp = _now()
    
    # Produce a relative posix path so the link is clickable in markdown renderers
    rel = _relpath_posix(page, execution_file)
    filename = Path(execution_file).name
    
    entry = (
        f"###  {tool_name} @ {timestamp}\n\n"
        f"[Open file]({rel})  |  **File name:** `{filename}`\n\n"
        f"_Last updated {timestamp}_\n\n"
    )
    
    _append_markdown(page, entry)
    logger.info(f"[UI SINK] Updated index file with entry for {tool_name}")

async def publish_ui_blocks(ctx: CallbackContext, tool_name: str, blocks: List[Dict[str, Any]]):
    """
    Publish UI blocks to an individual tool execution file, and update the index.
    
    Blocks schema (tools can return any subset):
      {"type":"markdown","title":"...","content":"..."}
      {"type":"table","title":"...","rows":[["col1","col2"],["v1","v2"],...]}
      {"type":"artifact_list","title":"...","files":["plot_1.png","report.pdf"]}
    """
    print("DEBUG: publish_ui_blocks called")
    logger = _get_logger()
    logger.info(f"[UI SINK] publish_ui_blocks called for tool: {tool_name}, blocks count: {len(blocks)}")
    
    try:
        # Create individual file for this tool execution
        execution_file = _create_tool_execution_file(ctx, tool_name, blocks)
        print(f"DEBUG: execution_file = {execution_file}")
        logger.info(f"[UI SINK] Created execution file: {execution_file}")
        
        # Update index file
        _update_index_file(ctx, tool_name, execution_file)
        
        # Save both files as artifacts
        try:
            from google.genai import types
            import asyncio

            page = ensure_ui_page(ctx)
            rel_for_artifact = _relpath_posix(page, execution_file)

            # Save the individual execution file
            try:
                with open(execution_file, "rb") as f:
                    blob = types.Blob(data=f.read(), mime_type="text/markdown")
                part = types.Part(inline_data=blob)
                await ctx.save_artifact(rel_for_artifact, part)
                logger.info(f"[UI SINK] [OK] Saved execution artifact: {rel_for_artifact}")
            except Exception as e:
                logger.error(f"[UI SINK] [FAILED] to save execution artifact '{rel_for_artifact}': {e}")

            # Save the index file
            try:
                with open(page, "rb") as f:
                    blob = types.Blob(data=f.read(), mime_type="text/markdown")
                part = types.Part(inline_data=blob)
                await ctx.save_artifact(UI_FILENAME, part)
                logger.info(f"[UI SINK] [OK] Saved index artifact: {UI_FILENAME}")
            except Exception as e:
                logger.error(f"[UI SINK] [FAILED] to save index artifact '{UI_FILENAME}': {e}")
        except Exception as e:
            logger.warning(f"[UI SINK] Failed to save artifacts: {e}")
            
        logger.info(f"[UI SINK] [OK] publish_ui_blocks completed successfully for {tool_name}")
    except Exception as e:
        logger.error(f"[UI SINK] [X] Error in publish_ui_blocks: {e}", exc_info=True)

