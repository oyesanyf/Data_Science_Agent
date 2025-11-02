# -*- coding: utf-8 -*-
"""
Workflow State Persistence

Ensures workflow state (current stage, progress) persists across server restarts.
Integrates with ADK session service to save/restore workflow position.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def save_workflow_state(state: Dict[str, Any], stage_id: int, action: str = "next", step_id: Optional[int] = None) -> None:
    """
    Save workflow state to session state for persistence across restarts.
    
    Args:
        state: Session state dictionary
        stage_id: Current workflow stage (1-11)
        action: Last action taken ("next", "back", "next_step", "back_step")
        step_id: Current step within stage (None = first step)
    """
    if not isinstance(state, dict):
        logger.warning("[WORKFLOW] Cannot save workflow state - state is not a dict")
        return
    
    try:
        state["workflow_stage"] = stage_id
        state["last_workflow_action"] = action
        state["workflow_updated_at"] = datetime.now().isoformat()
        
        # Track step within stage
        if step_id is not None:
            state["workflow_step"] = step_id
        elif "workflow_step" not in state:
            state["workflow_step"] = 0  # Default to first step
        
        # Track workflow history (last 10 transitions)
        if "workflow_history" not in state:
            state["workflow_history"] = []
        
        history = state["workflow_history"]
        history.append({
            "stage_id": stage_id,
            "step_id": state.get("workflow_step", 0),
            "action": action,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 entries
        if len(history) > 10:
            state["workflow_history"] = history[-10:]
        
        step_info = f", Step {state.get('workflow_step', 0)}" if step_id is not None or "workflow_step" in state else ""
        logger.info(f"[WORKFLOW] ✅ Saved workflow state: Stage {stage_id}{step_info} (action: {action})")
        
    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to save workflow state: {e}")


def restore_workflow_state(state: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    """
    Restore workflow state from session state.
    
    Args:
        state: Session state dictionary
        
    Returns:
        Tuple of (stage_id, step_id) or (None, None) if not found
    """
    if not isinstance(state, dict):
        return None, None
    
    try:
        stage_id = state.get("workflow_stage")
        step_id = state.get("workflow_step", 0)
        
        if stage_id is not None:
            stage_id = int(stage_id)
            if 1 <= stage_id <= 11:  # Valid range for 11-stage workflow
                step_id = int(step_id) if step_id is not None else 0
                last_action = state.get("last_workflow_action", "unknown")
                logger.debug(f"[WORKFLOW] ✅ Restored workflow state: Stage {stage_id}, Step {step_id} (last action: {last_action})")
                return stage_id, step_id
            else:
                logger.warning(f"[WORKFLOW] Invalid workflow stage: {stage_id}, resetting to 1")
                state["workflow_stage"] = 1
                state["workflow_step"] = 0
                return 1, 0
        else:
            logger.info("[WORKFLOW] No saved workflow state found")
            return None, None
            
    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to restore workflow state: {e}")
        return None, None


def get_workflow_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current workflow information including stage, history, and next steps.
    
    Args:
        state: Session state dictionary
        
    Returns:
        Dictionary with workflow information
    """
    if not isinstance(state, dict):
        return {
            "stage_id": 1,
            "stage_name": "Data Collection & Ingestion",
            "message": "Workflow state not available"
        }
    
    try:
        from .ds_tools import WORKFLOW_STAGES
        
        current_stage = state.get("workflow_stage", 1)
        if not (1 <= current_stage <= 11):
            current_stage = 1
        
        stage = WORKFLOW_STAGES[current_stage - 1]
        
        history = state.get("workflow_history", [])
        last_action = state.get("last_workflow_action", "unknown")
        started_at = state.get("workflow_started_at")
        updated_at = state.get("workflow_updated_at")
        
        info = {
            "stage_id": current_stage,
            "stage_name": stage["name"],
            "stage_icon": stage["icon"],
            "description": stage["description"],
            "tools": stage["tools"],
            "last_action": last_action,
            "workflow_started_at": started_at,
            "workflow_updated_at": updated_at,
            "history_length": len(history),
            "next_stage_id": (current_stage % 11) + 1,
            "prev_stage_id": ((current_stage - 2) % 11) + 1,
            "message": (
                f"{stage['icon']} **Current Stage: {stage['name']}**\n\n"
                f"**Description:** {stage['description']}\n\n"
                f"**Progress:** Stage {current_stage} of 11\n"
                f"**Last Action:** {last_action}\n"
                f"**Next:** Stage {(current_stage % 11) + 1} - {WORKFLOW_STAGES[(current_stage % 11)]['name']}\n"
                f"**Previous:** Stage {((current_stage - 2) % 11) + 1} - {WORKFLOW_STAGES[((current_stage - 2) % 11)]['name']}\n"
            )
        }
        
        if started_at:
            info["message"] += f"\n**Workflow Started:** {started_at}\n"
        
        return info
        
    except Exception as e:
        logger.error(f"[WORKFLOW] Failed to get workflow info: {e}")
        return {
            "stage_id": 1,
            "stage_name": "Data Collection & Ingestion",
            "message": f"Error getting workflow info: {e}"
        }

