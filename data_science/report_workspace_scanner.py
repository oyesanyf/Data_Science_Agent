"""
Workspace Scanner for Executive Report Generation

This module scans the workspace for all tool outputs and organizes them
into appropriate report sections. It ensures that all EDA, data quality,
feature engineering, prediction, and other outputs are included in reports.

Categories:
- EDA: analyze_dataset, describe, plot, stats, correlation
- Data Quality: clean, validate, impute, handle_outliers
- Feature Engineering: scale_data, encode, feature_selection, transform
- Predictions: predict, forecast
- Model Training: train, hpo, grid_search, automl
- Evaluation: evaluate, explain, shap
- Time Series: prophet, arima, sarima
- Causal: causal_discovery, causal_inference
- Fairness: fairness, bias_detection
- Drift: drift_detection, data_quality_monitor
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Tool to section mapping
TOOL_SECTIONS = {
    # EDA tools
    "analyze_dataset": "EDA",
    "describe": "EDA",
    "plot": "EDA",
    "stats": "EDA",
    "correlation": "EDA",
    "outlier_detection": "EDA",
    
    # Data Quality tools
    "clean": "Data Quality",
    "validate": "Data Quality",
    "impute": "Data Quality",
    "handle_outliers": "Data Quality",
    "detect_data_quality": "Data Quality",
    "robust_auto_clean_file": "Data Quality",
    
    # Feature Engineering tools
    "scale_data": "Feature Engineering",
    "encode": "Feature Engineering",
    "feature_selection": "Feature Engineering",
    "transform": "Feature Engineering",
    "create_interactions": "Feature Engineering",
    "polynomial_features": "Feature Engineering",
    
    # Prediction tools
    "predict": "Predictions",
    "forecast": "Predictions",
    "prophet": "Predictions",
    
    # Model Training tools
    "train": "Model Training",
    "train_baseline_model": "Model Training",
    "train_classifier": "Model Training",
    "train_regressor": "Model Training",
    "train_decision_tree": "Model Training",
    "train_knn": "Model Training",
    "train_naive_bayes": "Model Training",
    "train_svm": "Model Training",
    "train_dl_classifier": "Model Training",
    "train_dl_regressor": "Model Training",
    "train_dl": "Model Training",
    "smart_autogluon_automl": "Model Training",
    "smart_autogluon_timeseries": "Model Training",
    "auto_sklearn_classify": "Model Training",
    "auto_sklearn_regress": "Model Training",
    "autogluon_automl": "Model Training",
    "autogluon_timeseries": "Model Training",
    "ensemble": "Model Training",
    "hpo": "Model Training",
    "grid_search": "Model Training",
    "optuna_tune": "Model Training",
    "automl": "Model Training",
    
    # Evaluation tools
    "evaluate": "Model Evaluation",
    "explain": "Model Evaluation",
    "shap": "Model Evaluation",
    "feature_importance": "Model Evaluation",
    
    # Time Series tools
    "arima": "Time Series",
    "sarima": "Time Series",
    "decompose": "Time Series",
    
    # Causal tools
    "causal_discovery": "Causal Analysis",
    "causal_inference": "Causal Analysis",
    
    # Fairness tools
    "fairness": "Fairness & Governance",
    "bias_detection": "Fairness & Governance",
    "fairness_metrics": "Fairness & Governance",
    
    # Drift tools
    "drift_detection": "Drift Monitoring",
    "data_quality_monitor": "Drift Monitoring",
    
    # Q&A tool
    "question": "Questions & Answers",
}


def collect_workspace_outputs(tool_context: Optional[Any] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scan workspace for all tool outputs and organize by section.
    
    Returns:
        Dict mapping section names to lists of output data
    """
    outputs_by_section = {
        "EDA": [],
        "Data Quality": [],
        "Feature Engineering": [],
        "Predictions": [],
        "Model Training": [],
        "Model Evaluation": [],
        "Time Series": [],
        "Causal Analysis": [],
        "Fairness & Governance": [],
        "Drift Monitoring": [],
        "Questions & Answers": [],  # NEW: Q&A section
    }
    
    # Get workspace root
    workspace_root = None
    if tool_context:
        state = getattr(tool_context, "state", {})
        workspace_root = state.get("workspace_root")
    
    if not workspace_root:
        # Try to get from artifact_manager
        try:
            from . import artifact_manager
            workspace_root = artifact_manager.get_default_workspace()
        except Exception:
            logger.warning("[WORKSPACE SCANNER] Could not determine workspace root")
            return outputs_by_section
    
    # Check results directory for structured JSON output files (NEW: dedicated results/ folder)
    results_dir = Path(workspace_root) / "results"
    if not results_dir.exists():
        # Fallback: check reports directory for backwards compatibility
        reports_dir = Path(workspace_root) / "reports"
        if not reports_dir.exists():
            logger.info("[WORKSPACE SCANNER] No results or reports directory found")
            return outputs_by_section
        results_dir = reports_dir
    
    # Scan all JSON output files in results directory
    output_files = sorted(results_dir.glob("*_output_*.json"), key=os.path.getmtime, reverse=True)
    
    logger.info(f"[WORKSPACE SCANNER] Scanning {results_dir} for JSON output files")
    logger.info(f"[WORKSPACE SCANNER] Found {len(output_files)} output files in workspace")
    if output_files:
        logger.info(f"[WORKSPACE SCANNER] Output files: {[f.name for f in output_files[:10]]}")
    else:
        logger.warning(f"[WORKSPACE SCANNER] No output files found! Looking in: {results_dir}")
    
    for output_file in output_files:
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                output_data = json.load(f)
            
            tool_name = output_data.get("tool_name", "unknown")
            
            # Remove common suffixes for mapping
            # Remove "_tool" suffix if present
            clean_tool_name = tool_name.replace("_tool", "")
            # Also remove "_guard" suffix (from workflow guards)
            clean_tool_name = clean_tool_name.replace("_guard", "")
            
            logger.debug(f"[WORKSPACE SCANNER] Tool: {tool_name} → Clean: {clean_tool_name}")
            
            # Also check for training-related keywords if not found in mapping
            section = TOOL_SECTIONS.get(clean_tool_name, None)
            
            # Fallback: Check if tool name contains training keywords
            if section is None:
                training_keywords = ["train", "autogluon", "automl", "ensemble", "classifier", "regressor", "model"]
                if any(keyword in clean_tool_name.lower() for keyword in training_keywords):
                    section = "Model Training"
                    logger.info(f"[WORKSPACE SCANNER] Mapped '{tool_name}' → 'Model Training' (keyword match)")
                else:
                    section = "Other"
                    logger.debug(f"[WORKSPACE SCANNER] Mapped '{tool_name}' → 'Other'")
            else:
                logger.info(f"[WORKSPACE SCANNER] Mapped '{tool_name}' → '{section}' (direct mapping)")
            
            # Add to appropriate section
            if section in outputs_by_section:
                outputs_by_section[section].append(output_data)
            else:
                # Create new section if needed
                if section not in outputs_by_section:
                    outputs_by_section[section] = []
                outputs_by_section[section].append(output_data)
        
        except Exception as e:
            logger.warning(f"[WORKSPACE SCANNER] Failed to read {output_file.name}: {e}")
    
    # Log summary
    for section, outputs in outputs_by_section.items():
        if outputs:
            logger.info(f"[WORKSPACE SCANNER] {section}: {len(outputs)} outputs")
    
    return outputs_by_section


def format_output_for_report(output: Dict[str, Any], section: str) -> str:
    """
    Format tool output for inclusion in PDF report.
    
    Args:
        output: Tool output data (from JSON file)
        section: Section name (e.g., "EDA", "Predictions")
    
    Returns:
        Formatted text suitable for PDF paragraph
    """
    try:
        tool_name = output.get("tool_name", "Unknown Tool")
        timestamp = output.get("timestamp", "")
        status = output.get("status", "unknown")
        display = output.get("display", "")
        metrics = output.get("metrics", {})
        artifacts = output.get("artifacts", [])
        
        # Build formatted text
        parts = []
        
        # Tool header
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
                parts.append(f"<b>{tool_name}</b> ({time_str})")
            except Exception:
                parts.append(f"<b>{tool_name}</b>")
        else:
            parts.append(f"<b>{tool_name}</b>")
        
        # Status indicator
        if status == "success":
            parts.append("✅ Completed successfully")
        elif status == "failed":
            parts.append("❌ Failed")
        
        # Display text (truncate if too long)
        if display:
            # Remove markdown formatting for PDF
            clean_display = display.replace("**", "").replace("✅", "").replace("🔄", "").replace("⚠️", "")
            clean_display = clean_display.strip()
            
            # Truncate if too long
            if len(clean_display) > 500:
                clean_display = clean_display[:500] + "..."
            
            parts.append(clean_display)
        
        # Key metrics (if available)
        if metrics and isinstance(metrics, dict):
            metric_strs = []
            for key, value in list(metrics.items())[:5]:  # Max 5 metrics
                if not key.startswith("_") and isinstance(value, (int, float)):
                    if isinstance(value, float):
                        metric_strs.append(f"{key}: {value:.3f}")
                    else:
                        metric_strs.append(f"{key}: {value}")
            if metric_strs:
                parts.append("Key Metrics: " + ", ".join(metric_strs))
        
        # Artifacts (if available)
        if artifacts:
            artifact_count = len(artifacts) if isinstance(artifacts, list) else 1
            parts.append(f"Generated {artifact_count} artifact(s)")
        
        return " | ".join(parts)
    
    except Exception as e:
        logger.warning(f"[FORMAT OUTPUT] Error formatting output: {e}")
        return f"<b>{output.get('tool_name', 'Tool')}</b> - Output formatting error"


def get_recent_outputs(section: str, limit: int = 5, tool_context: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Get the most recent outputs for a specific section.
    
    Args:
        section: Section name (e.g., "EDA", "Predictions")
        limit: Maximum number of outputs to return
        tool_context: Optional tool context for workspace resolution
    
    Returns:
        List of output data dictionaries
    """
    all_outputs = collect_workspace_outputs(tool_context=tool_context)
    section_outputs = all_outputs.get(section, [])
    return section_outputs[:limit]
