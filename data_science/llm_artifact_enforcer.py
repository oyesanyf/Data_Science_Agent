# -*- coding: utf-8 -*-
"""
LLM-Enforced Artifact Creation System

Uses LLM to validate and enforce that artifacts are:
1. Created and saved to UI (via ADK artifact service)
2. Saved as MD files with results
3. Saved to workspace filesystem

The LLM validates tool results to ensure all required artifacts are generated.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Tools logger for artifact operations
try:
    from .logging_config import get_tools_logger
    tools_logger = get_tools_logger()
except ImportError:
    tools_logger = logger  # Fallback to default logger

# Try to import LLM libraries
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    try:
        from openai import OpenAI
        OPENAI_AVAILABLE = True
        _openai_client = None
    except ImportError:
        OPENAI_AVAILABLE = False

try:
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def _get_llm_client():
    """Get LLM client for artifact validation."""
    global _openai_client
    if LITELLM_AVAILABLE:
        return None  # Use litellm directly
    elif OPENAI_AVAILABLE:
        if _openai_client is None:
            _openai_client = OpenAI()
        return _openai_client
    return None


def _call_llm(prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    """
    Call LLM to validate or generate artifact requirements.
    
    Args:
        prompt: LLM prompt
        model: Model name to use
        
    Returns:
        LLM response or None if LLM unavailable
    """
    try:
        if LITELLM_AVAILABLE:
            response = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        elif OPENAI_AVAILABLE:
            client = _get_llm_client()
            if client:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"[LLM ENFORCER] LLM call failed: {e}")
    return None


def llm_validate_artifact_requirements(
    tool_name: str,
    result: Dict[str, Any],
    tool_context: Any = None
) -> Dict[str, List[str]]:
    """
    Use LLM to analyze tool result and determine what artifacts should be created.
    
    Args:
        tool_name: Name of the tool
        result: Tool result dictionary
        tool_context: ADK tool context
        
    Returns:
        Dictionary with required artifact types and descriptions
    """
    # Build context for LLM
    result_summary = json.dumps(result, default=str, indent=2)[:1000]  # Truncate for LLM
    
    prompt = f"""Analyze this tool execution result and determine what artifacts must be created:

Tool: {tool_name}
Result Summary:
{result_summary}

Based on ADK best practices, determine which artifacts are REQUIRED:
1. Markdown summary (MD file with formatted results)
2. File artifacts (if result contains model_path, plot_path, report_path, etc.)
3. JSON summary (for LLM accessibility via {{artifact.filename}})

Return ONLY a JSON object with this structure:
{{
    "required_artifacts": [
        {{
            "type": "markdown",
            "filename": "tool_name_output.md",
            "description": "Markdown summary of tool execution",
            "required": true
        }},
        {{
            "type": "file",
            "filename": "actual_filename",
            "source_path": "path_from_result",
            "description": "Actual file artifact",
            "required": true
        }},
        {{
            "type": "json_summary",
            "filename": "tool_name_summary.json",
            "description": "JSON summary for LLM access",
            "required": true
        }}
    ],
    "validation_checks": [
        "artifact_must_be_saved_to_ui",
        "artifact_must_be_saved_to_filesystem",
        "artifact_must_be_markdown_with_results"
    ]
}}

Return ONLY the JSON, no other text:"""

    response = _call_llm(prompt)
    
    if not response:
        # Fallback: return default requirements
        return {
            "required_artifacts": [
                {
                    "type": "markdown",
                    "filename": f"{tool_name}_output.md",
                    "required": True
                },
                {
                    "type": "json_summary",
                    "filename": f"{tool_name}_summary.json",
                    "required": True
                }
            ],
            "validation_checks": [
                "artifact_must_be_saved_to_ui",
                "artifact_must_be_saved_to_filesystem",
                "artifact_must_be_markdown_with_results"
            ]
        }
    
    # Parse LLM response (should be JSON)
    try:
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        
        requirements = json.loads(response)
        logger.info(f"[LLM ENFORCER] LLM determined {len(requirements.get('required_artifacts', []))} required artifacts")
        return requirements
    except Exception as e:
        logger.warning(f"[LLM ENFORCER] Failed to parse LLM response: {e}")
        # Return default
        return {
            "required_artifacts": [
                {"type": "markdown", "filename": f"{tool_name}_output.md", "required": True}
            ],
            "validation_checks": ["artifact_must_be_saved_to_ui", "artifact_must_be_saved_to_filesystem"]
        }


def llm_enforce_artifact_creation(
    tool_name: str,
    result: Dict[str, Any],
    tool_context: Any = None
) -> Dict[str, Any]:
    """
    Use LLM to enforce artifact creation - validates and creates missing artifacts.
    
    This function:
    1. Uses LLM to determine required artifacts
    2. Checks if they exist
    3. Creates missing artifacts
    4. Validates all artifacts were created correctly
    5. Saves markdown with results to filesystem
    6. Saves to UI via ADK artifact service
    
    Args:
        tool_name: Name of the tool
        result: Tool result dictionary
        tool_context: ADK tool context
        
    Returns:
        Updated result with artifact information
    """
    if not isinstance(result, dict):
        result = {"status": "success", "data": result}
    
    # Step 1: Get LLM-determined requirements
    requirements = llm_validate_artifact_requirements(tool_name, result, tool_context)
    required_artifacts = requirements.get("required_artifacts", [])
    validation_checks = requirements.get("validation_checks", [])
    
    # Step 2: Ensure workspace exists (try multiple methods)
    workspace_root = None
    if tool_context and hasattr(tool_context, 'state'):
        # Try to rehydrate workspace state first
        try:
            from . import artifact_manager
            artifact_manager.rehydrate_session_state(tool_context.state)
            from .large_data_config import UPLOAD_ROOT
            artifact_manager.ensure_workspace(tool_context.state, UPLOAD_ROOT)
        except Exception as e:
            logger.debug(f"[LLM ENFORCER] Could not rehydrate workspace: {e}")
        
        workspace_root = tool_context.state.get('workspace_root')
    
    # Fallback: Try to find workspace on disk
    if not workspace_root:
        try:
            from .large_data_config import UPLOAD_ROOT
            from glob import glob
            
            workspace_pattern = os.path.join(UPLOAD_ROOT, "_workspaces", "*", "*")
            workspaces = glob(workspace_pattern)
            
            if workspaces:
                latest_workspace = max(workspaces, key=os.path.getmtime)
                workspace_root = latest_workspace
                logger.info(f"[LLM ENFORCER] Using latest workspace from disk: {workspace_root}")
        except Exception as e:
            logger.debug(f"[LLM ENFORCER] Could not find workspace on disk: {e}")
    
    if not workspace_root:
        logger.warning(f"[LLM ENFORCER] No workspace_root found, skipping artifact enforcement")
        # Still return result - don't fail tool execution
        return result
    
    workspace_path = Path(workspace_root)
    reports_dir = workspace_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    tools_logger.info(f"[ARTIFACT] Workspace root: {workspace_root}, Reports folder: {reports_dir}")
    
    artifacts_created = []
    artifacts_failed = []
    
    # Step 3: Create required artifacts based on LLM analysis
    for artifact_req in required_artifacts:
        artifact_type = artifact_req.get("type")
        filename = artifact_req.get("filename")
        required = artifact_req.get("required", True)
        
        try:
            if artifact_type == "markdown":
                # Create markdown artifact with results
                md_path = _create_markdown_artifact(
                    tool_name=tool_name,
                    result=result,
                    filename=filename or f"{tool_name}_output.md",
                    workspace_dir=reports_dir
                )
                
                if md_path:
                    artifacts_created.append({
                        "type": "markdown",
                        "filename": md_path.name,
                        "path": str(md_path),
                        "saved_to_filesystem": True,
                        "saved_to_ui": False  # Will be set below
                    })
                    
                    # CRITICAL: Save to UI via ADK artifact service (like describe tool)
                    if tool_context and hasattr(tool_context, 'save_artifact'):
                        try:
                            from .logging_config import get_tools_logger
                            tools_logger = get_tools_logger()
                        except ImportError:
                            tools_logger = logger
                        
                        tools_logger.info(f"[ARTIFACT] Saving markdown artifact '{md_path.name}' to ADK service for tool '{tool_name}'")
                        ui_saved = _save_to_adk_service_safe(tool_context, md_path, md_path.name)
                        artifacts_created[-1]["saved_to_ui"] = ui_saved
                        if ui_saved:
                            tools_logger.info(f"[ARTIFACT] ✅ Saved markdown artifact '{md_path.name}' to ADK service for tool '{tool_name}'")
                            logger.info(f"[LLM ENFORCER] ✅ Saved markdown to ADK service: {md_path.name}")
                        else:
                            tools_logger.warning(f"[ARTIFACT] ⚠ Failed to save markdown artifact '{md_path.name}' to ADK service for tool '{tool_name}'")
                            logger.warning(f"[LLM ENFORCER] ⚠ Failed to save markdown to ADK service: {md_path.name}")
                    else:
                        try:
                            from .logging_config import get_tools_logger
                            tools_logger = get_tools_logger()
                        except ImportError:
                            tools_logger = logger
                        tools_logger.warning(f"[ARTIFACT] ⚠ No tool_context.save_artifact available for tool '{tool_name}'")
                        logger.warning(f"[LLM ENFORCER] ⚠ No tool_context.save_artifact available")
                    
                    try:
                        from .logging_config import get_tools_logger
                        tools_logger = get_tools_logger()
                    except ImportError:
                        tools_logger = logger
                    tools_logger.info(f"[ARTIFACT] ✅ Created markdown artifact '{md_path.name}' in folder '{reports_dir}' for tool '{tool_name}'")
                    logger.info(f"[LLM ENFORCER] ✅ Created markdown artifact: {md_path.name}")
            
            elif artifact_type == "file":
                # Handle file artifacts (from result)
                source_path = artifact_req.get("source_path")
                if source_path and os.path.exists(source_path):
                    _save_file_artifact(
                        tool_context=tool_context,
                        file_path=source_path,
                        workspace_dir=workspace_path,
                        filename=filename
                    )
                    artifacts_created.append({
                        "type": "file",
                        "filename": Path(source_path).name,
                        "path": source_path,
                        "saved_to_filesystem": True,
                        "saved_to_ui": tool_context is not None
                    })
            
            elif artifact_type == "json_summary":
                # Create JSON summary for LLM access
                json_path = _create_json_summary_artifact(
                    tool_name=tool_name,
                    result=result,
                    filename=filename or f"{tool_name}_summary.json",
                    workspace_dir=reports_dir
                )
                
                if json_path:
                    artifacts_created.append({
                        "type": "json_summary",
                        "filename": json_path.name,
                        "path": str(json_path),
                        "saved_to_filesystem": True,
                        "saved_to_ui": False  # Will be set below
                    })
                    
                    # CRITICAL: Save to UI via ADK artifact service
                    try:
                        from .logging_config import get_tools_logger
                        tools_logger = get_tools_logger()
                    except ImportError:
                        tools_logger = logger
                    
                    if tool_context and hasattr(tool_context, 'save_artifact'):
                        tools_logger.info(f"[ARTIFACT] Saving JSON summary artifact '{json_path.name}' to ADK service for tool '{tool_name}'")
                        ui_saved = _save_to_adk_service_safe(tool_context, json_path, json_path.name)
                        artifacts_created[-1]["saved_to_ui"] = ui_saved
                        if ui_saved:
                            tools_logger.info(f"[ARTIFACT] ✅ Saved JSON summary artifact '{json_path.name}' to ADK service for tool '{tool_name}'")
                            logger.info(f"[LLM ENFORCER] ✅ Saved JSON summary to ADK service: {json_path.name}")
                        else:
                            tools_logger.warning(f"[ARTIFACT] ⚠ Failed to save JSON summary artifact '{json_path.name}' to ADK service for tool '{tool_name}'")
                            logger.warning(f"[LLM ENFORCER] ⚠ Failed to save JSON summary to ADK service: {json_path.name}")
                    
                    tools_logger.info(f"[ARTIFACT] ✅ Created JSON summary artifact '{json_path.name}' in folder '{reports_dir}' for tool '{tool_name}'")
                    logger.info(f"[LLM ENFORCER] ✅ Created JSON summary: {json_path.name}")
        
        except Exception as e:
            logger.error(f"[LLM ENFORCER] Failed to create artifact {artifact_type}: {e}")
            if required:
                artifacts_failed.append({"type": artifact_type, "filename": filename, "error": str(e)})
    
    # Step 4: LLM validation of created artifacts
    validation_result = _llm_validate_artifacts(
        tool_name=tool_name,
        required_artifacts=required_artifacts,
        created_artifacts=artifacts_created,
        failed_artifacts=artifacts_failed,
        validation_checks=validation_checks
    )
    
    # Step 5: Update result with artifact information and ensure display fields
    if "artifacts" not in result:
        result["artifacts"] = []
    
    # Add all artifact filenames for LLM awareness
    for artifact in artifacts_created:
        artifact_filename = artifact.get("filename")
        if artifact_filename and artifact_filename not in result["artifacts"]:
            result["artifacts"].append(artifact_filename)
    
    # Ensure __display__ field exists (critical for ADK UI display)
    if "__display__" not in result:
        # Use existing message/ui_text or create from artifact info
        display_text = (
            result.get("message") or
            result.get("ui_text") or
            result.get("text") or
            f"✅ {tool_name} completed. Artifacts created: {', '.join([a.get('filename', '') for a in artifacts_created[:3]])}"
        )
        result["__display__"] = display_text
    
    # Add enforcement metadata
    result["llm_artifact_enforcement"] = {
        "required_count": len(required_artifacts),
        "created_count": len(artifacts_created),
        "failed_count": len(artifacts_failed),
        "validation": validation_result,
        "artifacts_created": artifacts_created,
        "artifacts_failed": artifacts_failed
    }
    
    # Add artifact placeholders for LLM access (enables {artifact.filename} in prompts)
    result["artifact_placeholders"] = {
        f"{{artifact.{art['filename']}}}": f"Content of {art['filename']}"
        for art in artifacts_created
        if art.get("filename")
    }
    
    # CRITICAL: Ensure message field exists (many UI systems check this)
    if "message" not in result or not result.get("message"):
        result["message"] = result["__display__"]
    
    logger.info(f"[LLM ENFORCER] ✅ Enforced artifacts: {len(artifacts_created)} created, {len(artifacts_failed)} failed")
    logger.info(f"[LLM ENFORCER] ✅ Result has __display__: {bool(result.get('__display__'))}")
    logger.info(f"[LLM ENFORCER] ✅ Result has artifacts list: {len(result.get('artifacts', []))}")
    
    return result


def _create_markdown_artifact(
    tool_name: str,
    result: Dict[str, Any],
    filename: str,
    workspace_dir: Path
) -> Optional[Path]:
    """
    Create markdown artifact with tool results - ALWAYS includes results.
    
    This function aggressively extracts data from multiple sources to ensure
    markdown files ALWAYS contain meaningful results, never empty placeholders.
    """
    try:
        md_lines = [
            f"# {tool_name.replace('_', ' ').title()} Output",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Tool:** `{tool_name}`",
            "",
            "---",
            ""
        ]
        
        # Add status
        status = result.get("status", "success")
        emoji = "✅" if status == "success" else "⚠️" if status == "warning" else "❌"
        md_lines.append(f"**Status:** {emoji} {status}")
        md_lines.append("")
        
        # ===== CRITICAL: ALWAYS CREATE RESULTS SECTION =====
        # Extract results from multiple sources with priority order
        md_lines.append("## Results")
        md_lines.append("")
        
        # Priority 1: Pre-formatted display text (best quality)
        display_text = (
            result.get("__display__") or
            result.get("message") or
            result.get("ui_text") or
            result.get("text") or
            result.get("content") or
            result.get("display") or
            result.get("_formatted_output")
        )
        
        if display_text and len(str(display_text).strip()) > 0:
            md_lines.append(str(display_text))
            md_lines.append("")
        else:
            # Priority 2: Extract from structured data fields
            results_added = False
            
            # Overview/Summary data (e.g., from describe tool)
            if result.get("overview"):
                try:
                    overview = result["overview"]
                    if isinstance(overview, str):
                        overview = json.loads(overview)
                    md_lines.append("### Statistical Summary")
                    md_lines.append("")
                    md_lines.append("```json")
                    md_lines.append(json.dumps(overview, indent=2))
                    md_lines.append("```")
                    md_lines.append("")
                    results_added = True
                except Exception as e:
                    md_lines.append(f"**Overview Data:** {str(result['overview'])[:500]}")
                    md_lines.append("")
                    results_added = True
            
            # Data/dataframe content
            if result.get("data") is not None:
                data_content = result["data"]
                if hasattr(data_content, 'to_markdown'):
                    md_lines.append("### Data")
                    md_lines.append("")
                    md_lines.append(data_content.to_markdown())
                    md_lines.append("")
                    results_added = True
                elif isinstance(data_content, (list, dict)):
                    md_lines.append("### Data")
                    md_lines.append("")
                    md_lines.append("```json")
                    md_lines.append(json.dumps(data_content, indent=2, default=str)[:2000])
                    md_lines.append("```")
                    md_lines.append("")
                    results_added = True
            
            # Summary field
            if result.get("summary"):
                md_lines.append("### Summary")
                md_lines.append("")
                md_lines.append(str(result["summary"]))
                md_lines.append("")
                results_added = True
            
            # Insights/AI-generated insights
            if result.get("insights"):
                md_lines.append("### Insights")
                md_lines.append("")
                insights = result["insights"]
                if isinstance(insights, list):
                    for i, insight in enumerate(insights, 1):
                        md_lines.append(f"{i}. {insight}")
                else:
                    md_lines.append(str(insights))
                md_lines.append("")
                results_added = True
            
            # If still no results, extract from ALL non-metadata fields
            if not results_added:
                md_lines.append("### Tool Output")
                md_lines.append("")
                # Include all non-metadata fields as results
                excluded_keys = {
                    "status", "artifacts", "llm_artifact_enforcement", 
                    "artifact_placeholders", "tool_context", "workspace_root"
                }
                for key, value in result.items():
                    if key not in excluded_keys and not key.startswith("_"):
                        if value is not None:
                            if isinstance(value, (dict, list)):
                                try:
                                    md_lines.append(f"**{key}:**")
                                    md_lines.append("```json")
                                    md_lines.append(json.dumps(value, indent=2, default=str)[:1000])
                                    md_lines.append("```")
                                    md_lines.append("")
                                except Exception:
                                    md_lines.append(f"**{key}:** {str(value)[:500]}")
                                    md_lines.append("")
                            else:
                                md_lines.append(f"**{key}:** {value}")
                                md_lines.append("")
                results_added = True
            
            # Final fallback - at minimum show status message
            if not results_added:
                md_lines.append(f"✅ Tool `{tool_name}` executed successfully.")
                if result.get("status"):
                    md_lines.append(f"Status: {result['status']}")
                md_lines.append("")
        
        # ===== ADDITIONAL DATA SECTIONS =====
        
        # Metrics section
        if result.get("metrics"):
            md_lines.append("## Metrics")
            md_lines.append("")
            metrics = result.get("metrics", {})
            if isinstance(metrics, dict):
                for key, value in metrics.items():
                    if not key.startswith("_"):
                        if isinstance(value, (dict, list)):
                            md_lines.append(f"**{key}:**")
                            md_lines.append("```json")
                            md_lines.append(json.dumps(value, indent=2, default=str)[:500])
                            md_lines.append("```")
                        else:
                            md_lines.append(f"- **{key}:** {value}")
                md_lines.append("")
        
        # Data summary (shape, columns, etc.)
        has_data_summary = False
        if result.get("shape"):
            has_data_summary = True
            md_lines.append("## Data Summary")
            md_lines.append("")
            shape = result.get("shape")
            if isinstance(shape, (list, tuple)) and len(shape) == 2:
                md_lines.append(f"- **Rows:** {shape[0]:,}")
                md_lines.append(f"- **Columns:** {shape[1]}")
            else:
                md_lines.append(f"- **Shape:** {shape}")
            md_lines.append("")
        
        if result.get("columns"):
            if not has_data_summary:
                md_lines.append("## Data Summary")
                md_lines.append("")
            columns = result.get("columns")
            md_lines.append(f"- **Total Columns:** {len(columns) if isinstance(columns, (list, tuple)) else 'N/A'}")
            if isinstance(columns, (list, tuple)) and len(columns) <= 20:
                md_lines.append(f"- **Column Names:** {', '.join(str(c) for c in columns)}")
            md_lines.append("")
        
        # Missing values info
        if result.get("missing_values"):
            missing = result["missing_values"]
            if isinstance(missing, dict) and missing:
                md_lines.append("### Missing Values")
                md_lines.append("")
                for col, count in list(missing.items())[:10]:
                    md_lines.append(f"- **{col}:** {count} missing")
                md_lines.append("")
        
        # Artifacts list
        if result.get("artifacts"):
            md_lines.append("## Generated Artifacts")
            md_lines.append("")
            artifacts = result.get("artifacts", [])
            for artifact in artifacts[:20]:
                artifact_name = str(artifact).split('/')[-1].split('\\')[-1]
                md_lines.append(f"- `{artifact_name}`")
            md_lines.append("")
        
        # Footer
        md_lines.append("---")
        md_lines.append(f"*Generated by LLM-Enforced Artifact System*")
        
        # ===== VALIDATION: Ensure markdown has meaningful content =====
        full_content = "\n".join(md_lines)
        
        # Check if markdown has actual results (not just headers/metadata)
        result_indicators = [
            "## Results", "### Statistical Summary", "### Data", "### Summary",
            "### Insights", "### Tool Output", "```json", "```", "|"
        ]
        has_results = any(indicator in full_content for indicator in result_indicators)
        
        if not has_results:
            logger.warning(f"[LLM ENFORCER] ⚠ Markdown may lack results, adding fallback content")
            # Inject a fallback message into Results section
            results_idx = None
            for i, line in enumerate(md_lines):
                if line == "## Results":
                    results_idx = i + 2
                    break
            
            if results_idx:
                fallback = [
                    "",
                    "> ⚠ **Note:** Tool executed but no structured results were available.",
                    "",
                    "**Raw Result Keys:** " + ", ".join([k for k in result.keys() if not k.startswith("_")][:10]),
                    ""
                ]
                md_lines[results_idx:results_idx] = fallback
        
        # Save to filesystem
        md_path = workspace_dir / filename
        tools_logger.info(f"[ARTIFACT] Creating markdown artifact '{filename}' in folder '{workspace_dir}'")
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        
        # Validate file was created and has meaningful content
        if md_path.exists():
            file_size = md_path.stat().st_size
            if file_size > 200:  # At least 200 bytes (headers + some content)
                # Double-check content quality
                file_content = md_path.read_text(encoding="utf-8", errors="ignore")
                # Count actual content lines (not just headers/metadata)
                content_lines = [l for l in file_content.split("\n") 
                               if l.strip() and not l.startswith("#") and not l.startswith("**Generated") 
                               and not l.startswith("**Status") and not l.startswith("---") 
                               and not l.startswith("*Generated")]
                
                if len(content_lines) >= 3:  # At least 3 lines of actual content
                    tools_logger.info(f"[ARTIFACT] ✅ Created markdown artifact '{filename}' in '{workspace_dir}' ({file_size} bytes, {len(content_lines)} content lines)")
                    logger.info(f"[LLM ENFORCER] ✅ Created markdown artifact: {md_path} ({file_size} bytes, {len(content_lines)} content lines)")
                    return md_path
                else:
                    tools_logger.warning(f"[ARTIFACT] ⚠ Markdown artifact '{filename}' has limited content ({len(content_lines)} content lines)")
                    logger.warning(f"[LLM ENFORCER] ⚠ Markdown file exists but has limited content: {md_path} ({len(content_lines)} content lines)")
                    # Still return it - better than nothing
                    return md_path
            else:
                tools_logger.error(f"[ARTIFACT] ✗ Markdown artifact '{filename}' too small ({file_size} bytes)")
                logger.error(f"[LLM ENFORCER] ❌ Markdown file too small: {md_path} ({file_size} bytes)")
                return None
        else:
            tools_logger.error(f"[ARTIFACT] ✗ Markdown artifact '{filename}' was not created in folder '{workspace_dir}'")
            logger.error(f"[LLM ENFORCER] ❌ Markdown file was not created: {md_path}")
            return None
        
    except Exception as e:
        logger.error(f"[LLM ENFORCER] Failed to create markdown artifact: {e}", exc_info=True)
        return None


def _create_json_summary_artifact(
    tool_name: str,
    result: Dict[str, Any],
    filename: str,
    workspace_dir: Path
) -> Optional[Path]:
    """Create JSON summary artifact for LLM accessibility."""
    try:
        summary = {
            "tool": tool_name,
            "status": result.get("status", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": result.get("message", ""),
            "metrics": result.get("metrics", {}),
            "overview": result.get("overview", {}),
            "shape": result.get("shape"),
            "columns": result.get("columns"),
            "artifacts": result.get("artifacts", []),
            "artifact_placeholders": result.get("artifact_placeholders", {})
        }
        
        # Remove None values
        summary = {k: v for k, v in summary.items() if v is not None}
        
        # Save to filesystem
        json_path = workspace_dir / filename
        tools_logger.info(f"[ARTIFACT] Creating JSON summary artifact '{filename}' in folder '{workspace_dir}'")
        json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        
        file_size = json_path.stat().st_size if json_path.exists() else 0
        tools_logger.info(f"[ARTIFACT] ✅ Created JSON summary artifact '{filename}' in folder '{workspace_dir}' ({file_size} bytes)")
        logger.info(f"[LLM ENFORCER] Created JSON summary: {json_path}")
        return json_path
        
    except Exception as e:
        tools_logger.error(f"[ARTIFACT] ✗ Failed to create JSON summary artifact '{filename}': {e}")
        logger.error(f"[LLM ENFORCER] Failed to create JSON summary: {e}")
        return None


def _save_file_artifact(
    tool_context: Any,
    file_path: str,
    workspace_dir: Path,
    filename: Optional[str] = None
) -> bool:
    """Save file artifact to workspace and ADK service."""
    try:
        path = Path(file_path)
        if not path.exists():
            return False
        
        # Determine workspace subdirectory based on file type
        if path.suffix.lower() in ['.pkl', '.joblib', '.onnx', '.h5', '.pt', '.pth']:
            dest_dir = workspace_dir / "models"
        elif path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg', '.gif']:
            dest_dir = workspace_dir / "plots"
        elif path.suffix.lower() in ['.pdf', '.html']:
            dest_dir = workspace_dir / "reports"
        else:
            dest_dir = workspace_dir / "data"
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        tools_logger.info(f"[ARTIFACT] Created/verified artifact folder: {dest_dir}")
        
        # Copy to workspace
        dest_path = dest_dir / (filename or path.name)
        import shutil
        tools_logger.info(f"[ARTIFACT] Copying file artifact '{path.name}' to folder '{dest_dir}'")
        shutil.copy2(path, dest_path)
        
        file_size = dest_path.stat().st_size if dest_path.exists() else 0
        tools_logger.info(f"[ARTIFACT] ✅ Copied file artifact '{path.name}' to '{dest_dir}' ({file_size} bytes)")
        
        # Save to ADK service
        if tool_context and hasattr(tool_context, 'save_artifact'):
            tools_logger.info(f"[ARTIFACT] Saving file artifact '{dest_path.name}' to ADK service")
            saved_to_adk = _save_to_adk_service_safe(tool_context, dest_path, dest_path.name)
            if saved_to_adk:
                tools_logger.info(f"[ARTIFACT] ✅ Saved file artifact '{dest_path.name}' to ADK service")
            else:
                tools_logger.warning(f"[ARTIFACT] ⚠ Failed to save file artifact '{dest_path.name}' to ADK service")
        
        logger.info(f"[LLM ENFORCER] Saved file artifact: {dest_path}")
        return True
        
    except Exception as e:
        logger.error(f"[LLM ENFORCER] Failed to save file artifact: {e}")
        return False


def _save_to_adk_service_safe(
    tool_context: Any,
    file_path: Path,
    artifact_name: str
) -> bool:
    """
    Safely save file to ADK artifact service using proper ADK pattern.
    
    Uses google.genai.types.Part and tool_context.save_artifact() as per ADK docs.
    """
    try:
        if not GENAI_AVAILABLE:
            logger.warning(f"[LLM ENFORCER] google.genai.types not available")
            return False
        
        if not hasattr(tool_context, 'save_artifact'):
            logger.warning(f"[LLM ENFORCER] tool_context has no save_artifact method")
            return False
        
        # Read file content
        if not file_path.exists():
            logger.error(f"[LLM ENFORCER] File does not exist: {file_path}")
            return False
        
        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            # Default based on extension
            if file_path.suffix.lower() == '.md':
                mime_type = "text/markdown"
            elif file_path.suffix.lower() == '.json':
                mime_type = "application/json"
            elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                mime_type = f"image/{file_path.suffix[1:].lower()}"
            else:
                mime_type = "text/plain"
        
        # Create Part object (ADK pattern)
        # For binary files or images, use inline_data Blob
        # For text files (markdown, JSON), use text field
        if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.pkl', '.joblib', '.bin']:
            file_data = file_path.read_bytes()
            artifact_part = types.Part(
                inline_data=types.Blob(mime_type=mime_type, data=file_data)
            )
        else:
            # Text-based files (markdown, JSON, txt, etc.)
            file_data = file_path.read_text(encoding='utf-8', errors='ignore')
            artifact_part = types.Part(text=file_data)
        
        # Save via ADK service (must be async-aware)
        import inspect
        if inspect.iscoroutinefunction(tool_context.save_artifact):
            # Async method - use proper async handling
            try:
                loop = asyncio.get_running_loop()
                # Create task in existing loop
                task = loop.create_task(tool_context.save_artifact(filename=artifact_name, artifact=artifact_part))
                # Don't await - let it run in background
                tools_logger.info(f"[ARTIFACT] Created async task to save artifact '{artifact_name}' to ADK service")
                logger.info(f"[LLM ENFORCER] Created async task to save: {artifact_name}")
                return True
            except RuntimeError:
                # No event loop - create one and run
                asyncio.run(tool_context.save_artifact(filename=artifact_name, artifact=artifact_part))
                tools_logger.info(f"[ARTIFACT] ✅ Saved artifact '{artifact_name}' to ADK service (async)")
                logger.info(f"[LLM ENFORCER] ✅ Saved to ADK service (async): {artifact_name}")
                return True
        else:
            # Sync method
            tool_context.save_artifact(filename=artifact_name, artifact=artifact_part)
            tools_logger.info(f"[ARTIFACT] ✅ Saved artifact '{artifact_name}' to ADK service (sync)")
            logger.info(f"[LLM ENFORCER] ✅ Saved to ADK service (sync): {artifact_name}")
            return True
            
    except Exception as e:
        logger.error(f"[LLM ENFORCER] Failed to save to ADK service: {e}", exc_info=True)
    
    return False


def _llm_validate_artifacts(
    tool_name: str,
    required_artifacts: List[Dict],
    created_artifacts: List[Dict],
    failed_artifacts: List[Dict],
    validation_checks: List[str]
) -> Dict[str, Any]:
    """
    Use LLM to validate that all required artifacts were created correctly.
    
    Args:
        tool_name: Tool name
        required_artifacts: LLM-determined required artifacts
        created_artifacts: Actually created artifacts
        failed_artifacts: Artifacts that failed to create
        validation_checks: Validation criteria from LLM
        
    Returns:
        Validation result dictionary
    """
    validation_summary = {
        "tool_name": tool_name,
        "required": len(required_artifacts),
        "created": len(created_artifacts),
        "failed": len(failed_artifacts),
        "compliance": {},
        "issues": [],
        "recommendations": []
    }
    
    # Check compliance with each validation check
    for check in validation_checks:
        if check == "artifact_must_be_saved_to_ui":
            ui_saved = sum(1 for art in created_artifacts if art.get("saved_to_ui", False))
            validation_summary["compliance"]["saved_to_ui"] = ui_saved == len(created_artifacts)
            if not validation_summary["compliance"]["saved_to_ui"]:
                validation_summary["issues"].append(f"Not all artifacts saved to UI ({ui_saved}/{len(created_artifacts)})")
        
        elif check == "artifact_must_be_saved_to_filesystem":
            fs_saved = sum(1 for art in created_artifacts if art.get("saved_to_filesystem", False))
            validation_summary["compliance"]["saved_to_filesystem"] = fs_saved == len(created_artifacts)
            if not validation_summary["compliance"]["saved_to_filesystem"]:
                validation_summary["issues"].append(f"Not all artifacts saved to filesystem ({fs_saved}/{len(created_artifacts)})")
        
        elif check == "artifact_must_be_markdown_with_results":
            has_markdown = any(art.get("type") == "markdown" for art in created_artifacts)
            validation_summary["compliance"]["has_markdown"] = has_markdown
            if not has_markdown:
                validation_summary["issues"].append("No markdown artifact with results created")
    
    # Use LLM to provide recommendations if issues found
    if validation_summary["issues"]:
        prompt = f"""Tool: {tool_name}
Required artifacts: {len(required_artifacts)}
Created: {len(created_artifacts)}
Failed: {len(failed_artifacts)}
Issues: {validation_summary['issues']}

Provide brief recommendations (one sentence each) to fix these artifact creation issues.
Return as JSON array: ["recommendation1", "recommendation2"]
"""
        
        response = _call_llm(prompt)
        if response:
            try:
                if "[" in response:
                    recommendations = json.loads(response)
                    validation_summary["recommendations"] = recommendations
            except Exception:
                pass
    
    return validation_summary

