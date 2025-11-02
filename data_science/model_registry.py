"""
Global Model Registry - Stores trained model paths for access by other tools.

All model training tools MUST register their models here.
All model inference/evaluation tools MUST read from here.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# Thread-safe global registry
_registry_lock = threading.Lock()
_model_registry: Dict[str, Dict[str, Any]] = {}

def register_model(
    model_name: str,
    model_path: str,
    model_type: str,
    target: str,
    metrics: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Register a trained model in the global registry.
    
    Args:
        model_name: Unique name for the model
        model_path: Full path to saved model file
        model_type: Type of model (e.g., "RandomForest", "XGBoost")
        target: Target column name
        metrics: Training metrics (accuracy, f1, etc.)
        metadata: Additional metadata
        workspace_root: Workspace directory for saving registry
        tool_context: Optional tool context for saving to ADK artifact system
    
    Returns:
        Registry entry dict
    """
    with _registry_lock:
        entry = {
            "model_name": model_name,
            "model_path": str(model_path),
            "model_type": model_type,
            "target": target,
            "metrics": metrics or {},
            "metadata": metadata or {},
            "registered_at": datetime.now().isoformat(),
            "last_used": None,
            "adk_artifact_saved": False
        }
        
        _model_registry[model_name] = entry
        logger.info(f"[MODEL REGISTRY] Registered: {model_name} -> {model_path}")
        
        # Store latest model info in session.state for ADK placeholder access
        # Agents can now use: {state.latest_model_name}, {state.latest_model_target} etc.
        if tool_context and hasattr(tool_context, 'state'):
            try:
                state = tool_context.state
                state['latest_model_name'] = model_name
                state['latest_model_type'] = model_type
                state['latest_model_target'] = target
                state['latest_model_artifact'] = f"{model_name}.joblib"
                state['latest_model_metadata'] = f"{model_name}_metadata.json"
                logger.info(f"[MODEL REGISTRY] 💡 Updated session.state - agents can use {{state.latest_model_name}}")
            except Exception as e:
                logger.debug(f"[MODEL REGISTRY] Could not update session state: {e}")
        
        # Save model to ADK artifact system (in addition to disk)
        if tool_context and Path(model_path).exists():
            try:
                from .artifact_utils import save_artifact_sync
                import json
                from google.genai.types import Part
                
                # 1. Save binary model file
                model_data = Path(model_path).read_bytes()
                artifact_filename = f"{model_name}.joblib"
                
                logger.info(f"[MODEL REGISTRY] Saving to ADK artifacts: {artifact_filename}")
                version = save_artifact_sync(tool_context, artifact_filename, model_data, "application/octet-stream")
                
                if version is not None:
                    entry["adk_artifact_saved"] = True
                    entry["adk_artifact_name"] = artifact_filename
                    entry["adk_artifact_version"] = version
                    logger.info(f"[MODEL REGISTRY] ✅ Model saved to ADK artifacts: {artifact_filename} v{version}")
                
                # 2. Save LLM-readable metadata as JSON artifact (for ADK placeholders!)
                # This allows agent instructions to reference: {artifact.ModelName_metadata.json}
                metadata_json = {
                    "model_name": model_name,
                    "model_type": model_type,
                    "target": target,
                    "metrics": metrics or {},
                    "registered_at": entry["registered_at"],
                    "artifact_name": artifact_filename,
                    "version": version,
                    "instructions": f"Use {{artifact.{artifact_filename}}} to reference this model in agent prompts"
                }
                
                metadata_filename = f"{model_name}_metadata.json"
                metadata_text = json.dumps(metadata_json, indent=2)
                
                logger.info(f"[MODEL REGISTRY] Saving metadata to ADK artifacts: {metadata_filename}")
                meta_version = save_artifact_sync(
                    tool_context, 
                    metadata_filename, 
                    metadata_text.encode('utf-8'), 
                    "application/json"
                )
                
                if meta_version is not None:
                    entry["metadata_artifact"] = metadata_filename
                    entry["metadata_version"] = meta_version
                    logger.info(f"[MODEL REGISTRY] ✅ Metadata saved: {metadata_filename} v{meta_version}")
                    logger.info(f"[MODEL REGISTRY] 💡 Agent can use: {{artifact.{metadata_filename}}} in instructions")
                
            except Exception as e:
                logger.warning(f"[MODEL REGISTRY] Could not save to ADK artifacts: {e}")
        
        # Save registry to disk
        if workspace_root:
            try:
                registry_dir = Path(workspace_root) / "models"
                registry_dir.mkdir(parents=True, exist_ok=True)
                registry_file = registry_dir / "model_registry.json"
                
                with open(registry_file, 'w', encoding='utf-8') as f:
                    json.dump(_model_registry, f, indent=2)
                
                logger.info(f"[MODEL REGISTRY] Saved to {registry_file}")
            except Exception as e:
                logger.error(f"[MODEL REGISTRY] Failed to save registry: {e}")
        
        return entry


def get_model(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a model entry from the registry.
    
    Args:
        model_name: Name of the model
    
    Returns:
        Model entry dict or None if not found
    """
    with _registry_lock:
        entry = _model_registry.get(model_name)
        if entry:
            # Update last_used timestamp
            entry["last_used"] = datetime.now().isoformat()
            logger.info(f"[MODEL REGISTRY] Retrieved: {model_name}")
        else:
            logger.warning(f"[MODEL REGISTRY] Model not found: {model_name}")
        return entry


def get_latest_model(target: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the most recently registered model, optionally filtered by target.
    
    Args:
        target: Optional target column to filter by
    
    Returns:
        Latest model entry or None
    """
    with _registry_lock:
        models = list(_model_registry.values())
        
        if target:
            models = [m for m in models if m.get("target") == target]
        
        if not models:
            logger.warning(f"[MODEL REGISTRY] No models found" + (f" for target '{target}'" if target else ""))
            return None
        
        # Sort by registration time (most recent first)
        models.sort(key=lambda m: m.get("registered_at", ""), reverse=True)
        latest = models[0]
        logger.info(f"[MODEL REGISTRY] Latest model: {latest['model_name']}")
        return latest


def list_models(target: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all registered models, optionally filtered by target.
    
    Args:
        target: Optional target column to filter by
    
    Returns:
        List of model entries
    """
    with _registry_lock:
        models = list(_model_registry.values())
        
        if target:
            models = [m for m in models if m.get("target") == target]
        
        logger.info(f"[MODEL REGISTRY] Listed {len(models)} models" + (f" for target '{target}'" if target else ""))
        return models


def load_registry_from_disk(workspace_root: str) -> bool:
    """
    Load model registry from disk.
    
    Args:
        workspace_root: Workspace directory
    
    Returns:
        True if loaded successfully, False otherwise
    """
    try:
        registry_file = Path(workspace_root) / "models" / "model_registry.json"
        
        if not registry_file.exists():
            logger.info(f"[MODEL REGISTRY] No registry file found at {registry_file}")
            return False
        
        with open(registry_file, 'r', encoding='utf-8') as f:
            loaded_registry = json.load(f)
        
        with _registry_lock:
            _model_registry.clear()
            _model_registry.update(loaded_registry)
        
        logger.info(f"[MODEL REGISTRY] Loaded {len(loaded_registry)} models from {registry_file}")
        return True
        
    except Exception as e:
        logger.error(f"[MODEL REGISTRY] Failed to load registry: {e}")
        return False


def create_model_md_artifact(
    model_entry: Dict[str, Any],
    workspace_root: str,
    additional_info: Optional[str] = None
) -> str:
    """
    Create a markdown artifact for a trained model.
    
    Args:
        model_entry: Model registry entry
        workspace_root: Workspace directory
        additional_info: Optional additional information
    
    Returns:
        Path to created markdown file
    """
    try:
        reports_dir = Path(workspace_root) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        model_name = model_entry["model_name"]
        md_path = reports_dir / f"{model_name}_training.md"
        
        # Build markdown content
        content_parts = [
            f"# Model Training Report: {model_name}\n",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "---\n\n",
            "## Model Information\n",
            f"- **Model Name:** `{model_name}`\n",
            f"- **Model Type:** {model_entry['model_type']}\n",
            f"- **Target Column:** {model_entry['target']}\n",
            f"- **Model Path:** `{model_entry['model_path']}`\n",
            f"- **Registered:** {model_entry['registered_at']}\n\n"
        ]
        
        # Add metrics
        if model_entry.get("metrics"):
            content_parts.append("## Training Metrics\n")
            for key, value in model_entry["metrics"].items():
                if isinstance(value, float):
                    content_parts.append(f"- **{key}:** {value:.4f}\n")
                else:
                    content_parts.append(f"- **{key}:** {value}\n")
            content_parts.append("\n")
        
        # Add metadata
        if model_entry.get("metadata"):
            content_parts.append("## Metadata\n")
            for key, value in model_entry["metadata"].items():
                if not key.startswith("_"):
                    content_parts.append(f"- **{key}:** {value}\n")
            content_parts.append("\n")
        
        # Add additional info
        if additional_info:
            content_parts.append("## Additional Information\n")
            content_parts.append(f"{additional_info}\n\n")
        
        content_parts.append("---\n")
        content_parts.append(f"*Model registered in global registry and ready for use by accuracy, evaluate, predict tools*\n")
        
        markdown_content = "".join(content_parts)
        
        md_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"[MODEL REGISTRY] Created artifact: {md_path}")
        
        return str(md_path)
        
    except Exception as e:
        logger.error(f"[MODEL REGISTRY] Failed to create MD artifact: {e}")
        return ""


def clear_registry():
    """Clear the entire registry (for testing)."""
    with _registry_lock:
        _model_registry.clear()
        logger.info("[MODEL REGISTRY] Cleared all models")

