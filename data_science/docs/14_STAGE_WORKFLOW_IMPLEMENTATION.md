# 14-Stage Sequential Workflow - Implementation Plan

## Overview

User Request: Implement a **14-stage sequential workflow** where:
- ✅ Users progress through stages 1→2→3→4...→14 in order
- ✅ System presents the **NEXT stage only** (not multiple stages)
- ✅ Users can navigate with `next_stage()` and `back_stage()` tools
- ✅ Users can jump directly: "go to step 10" or "back to step 1"
- ✅ **NEW Stage 9**: Prediction & Inference

## Current State

### Existing System (11 Stages)
1. Data Collection & Ingestion
2. Data Cleaning & Preparation
3. Exploratory Data Analysis (EDA)
4. Visualization
5. Feature Engineering
6. Statistical Analysis
7. Machine Learning Model Development
8. Model Evaluation & Validation
9. Model Deployment (Optional)
10. Report and Insights
11. Advanced & Specialized

### Issues
- ❌ Only 11 stages (need 14)
- ❌ Missing "Prediction & Inference" stage
- ❌ Stage 13 "Executive Report" and Stage 14 "Export PDF" not separated
- ❌ "Others" category not explicitly defined

## Target 14-Stage Workflow

### Complete 14-Stage Structure

```
Stage 1:  📥 Data Collection & Ingestion
Stage 2:  🧹 Data Cleaning & Preparation
Stage 3:  🔍 Exploratory Data Analysis (EDA)
Stage 4:  📊 Visualization
Stage 5:  ⚙️  Feature Engineering
Stage 6:  📈 Statistical Analysis
Stage 7:  🤖 Machine Learning Model Development
Stage 8:  ✅ Model Evaluation & Validation
Stage 9:  🎯 Prediction & Inference            ← NEW!
Stage 10: 🚀 Model Deployment (Optional)
Stage 11: 📝 Report and Insights
Stage 12: 🔬 Others (Specialized Methods)
Stage 13: 📊 Executive Report
Stage 14: 📄 Export Report as PDF
```

## Implementation Steps

### Step 1: Update WORKFLOW_STAGES in `ds_tools.py`

**File**: `data_science/ds_tools.py`  
**Location**: Lines 5585-5722

**Changes Needed**:

1. Keep stages 1-8 as is
2. **Insert NEW Stage 9**: Prediction & Inference
3. Renumber existing stages 9-11 to become 10-12
4. **Add Stage 13**: Executive Report
5. **Add Stage 14**: Export Report as PDF

**New Stage 9 Definition**:
```python
{
    "id": 9,
    "name": "Prediction & Inference",
    "icon": "🎯",
    "description": "Use trained model to make predictions on new or unseen data. Automate inference pipelines for real-time or batch predictions. Post-process predictions for decision support.",
    "tools": [
        "predict(target='column') - Make predictions on dataset",
        "inference() - Batch inference on new data",
        "load_model_universal_tool(action='predict') - Load model and predict",
        "classify() - Classification predictions",
        "forecast() - Time series predictions"
    ]
}
```

**New Stage 13 Definition**:
```python
{
    "id": 13,
    "name": "Executive Report",
    "icon": "📊",
    "description": "Create concise summaries for leadership audiences. Include KPIs, visual dashboards, and key takeaways.",
    "tools": [
        "export_executive_report(title='Executive Summary') - AI-generated executive report",
        "export_model_card() - Model governance documentation",
        "fairness_report() - Fairness and ethics summary"
    ]
}
```

**New Stage 14 Definition**:
```python
{
    "id": 14,
    "name": "Export Report as PDF",
    "icon": "📄",
    "description": "Generate and archive final outputs in standardized PDF format. Ensure reproducibility and documentation compliance.",
    "tools": [
        "export_executive_report() - Generate PDF executive report",
        "export(format='pdf') - Export technical report as PDF",
        "maintenance(action='list_workspaces') - View all workspace reports"
    ]
}
```

### Step 2: Update `next_stage()` Function

**File**: `data_science/ds_tools.py`  
**Location**: Lines 5726-5783

**Changes**:
```python
async def next_stage(tool_context=None) -> dict:
    """
    ➡️ Move to the next stage in the professional data science workflow.
    
    Advances you through the 14-stage workflow:
    1. Data Collection → 2. Cleaning → 3. EDA → 4. Visualization → 
    5. Feature Engineering → 6. Statistical Analysis → 7. ML Development → 
    8. Evaluation → 9. Prediction & Inference → 10. Deployment → 
    11. Reporting → 12. Others → 13. Executive Report → 14. Export PDF
    
    ...
    """
    # Get current stage from session state
    state = getattr(tool_context, "state", {}) if tool_context else {}
    current_stage = state.get("workflow_stage", 1)
    
    # Move to next stage (cycle back to 1 if at end)
    next_stage_id = (current_stage % 14) + 1  # ← Change from 11 to 14
    
    # Update state
    if tool_context:
        state["workflow_stage"] = next_stage_id
        state["last_workflow_action"] = "next"
    
    # Get stage info
    stage = WORKFLOW_STAGES[next_stage_id - 1]
    
    # Build display message
    message = (
        f"{stage['icon']} **Stage {stage['id']}: {stage['name']}**\n\n"
        f"**Description:** {stage['description']}\n\n"
        f"**Recommended Tools:**\n"
    )
    
    for i, tool in enumerate(stage['tools'], 1):
        message += f"{i}. `{tool}`\n"
    
    message += f"\n**Navigation:**\n"
    message += f"• `next_stage()` - Advance to Stage {(next_stage_id % 14) + 1}\n"  # ← Change
    message += f"• `back_stage()` - Return to Stage {(next_stage_id - 2) % 14 + 1}\n"  # ← Change
    message += f"• Say 'go to stage N' to jump to any stage\n"
    
    return {
        "status": "success",
        "current_stage": next_stage_id,
        "stage_name": stage['name'],
        "stage_icon": stage['icon'],
        "tools": stage['tools'],
        "message": message,
        "__display__": message
    }
```

### Step 3: Update `back_stage()` Function

**File**: `data_science/ds_tools.py`  
**Location**: Lines 5785-5842

**Changes**:
```python
async def back_stage(tool_context=None) -> dict:
    """
    ⬅️ Move to the previous stage in the professional data science workflow.
    
    Goes back through the 14-stage workflow:
    ...
    """
    # Get current stage from session state
    state = getattr(tool_context, "state", {}) if tool_context else {}
    current_stage = state.get("workflow_stage", 1)
    
    # Move to previous stage (wrap around if at beginning)
    prev_stage_id = ((current_stage - 2) % 14) + 1  # ← Change from 11 to 14
    
    # Update state
    if tool_context:
        state["workflow_stage"] = prev_stage_id
        state["last_workflow_action"] = "back"
    
    # Get stage info and build message (same as next_stage)
    ...
```

### Step 4: Update Agent System Prompt

**File**: `data_science/agent.py`  
**Location**: Lines 2849-2931

**Changes**:

1. Update workflow stage list from 11 to 14 stages
2. Add new Stage 9 description
3. Update stage navigation instructions

```python
"📊 PROFESSIONAL DATA SCIENCE WORKFLOW (14 STAGES)\n"
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
"\n"
"Follow this industry-standard workflow. Present options as NUMBERED lists:\n"
"\n"
"**Stage 1: Data Collection & Ingestion**\n"
"Gather data from multiple sources...\n"
...
"**Stage 9: Prediction & Inference** ← NEW!\n"
"Use trained model to make predictions on new or unseen data.\n"
"Automate inference pipelines for real-time or batch predictions.\n"
"1. `predict(target='column')` - Make predictions\n"
"2. `inference()` - Batch inference\n"
"3. `load_model_universal_tool(action='predict')` - Load and predict\n"
"4. `classify()` - Classification predictions\n"
"5. `forecast()` - Time series predictions\n"
"\n"
"**Stage 10: Model Deployment (Optional)**\n"
...
"**Stage 13: Executive Report**\n"
...
"**Stage 14: Export Report as PDF**\n"
...
```

### Step 5: Update Stage Selection Logic

**File**: `data_science/agent.py`  
**Location**: Lines 3113-3145

**Add**:
```python
"🤖 **After Training Model:**\n"
"   - MANDATORY → Present Stage 8 ONLY (evaluate, accuracy, explain_model)\n"
"\n"
"✅ **After Evaluation:**\n"
"   - Good results → Present Stage 9 ONLY (prediction & inference)\n"
"   - Poor results → Present Stage 5 ONLY (feature engineering) or Stage 7 (try different model)\n"
"\n"
"🎯 **After Prediction & Inference:**\n"
"   - Need to deploy → Present Stage 10 ONLY (model deployment)\n"
"   - Skip deployment → Present Stage 11 ONLY (report and insights)\n"
"\n"
"📝 **After Report and Insights:**\n"
"   - Need executive summary → Present Stage 13 ONLY (executive report)\n"
"   - Ready to export → Present Stage 14 ONLY (export PDF)\n"
```

### Step 6: Add Helper Function for Stage Jumping

**File**: `data_science/ds_tools.py`  
**Location**: After `back_stage()` function

**New Function**:
```python
@ensure_display_fields
async def goto_stage(stage_number: int, tool_context=None) -> dict:
    """
    🎯 Jump directly to a specific workflow stage.
    
    Args:
        stage_number: Stage number (1-14)
        tool_context: ADK tool context
    
    Returns:
        dict: Stage info with recommended tools
        
    Example:
        # Jump to Stage 9 (Prediction)
        result = await goto_stage(9)
        # Now in Stage 9 with prediction tools
    """
    # Validate stage number
    if not 1 <= stage_number <= 14:
        return {
            "status": "error",
            "message": f"Invalid stage number: {stage_number}. Must be between 1 and 14.",
            "__display__": f"❌ Invalid stage: {stage_number}. Valid stages: 1-14"
        }
    
    # Update state
    if tool_context:
        state = getattr(tool_context, "state", {})
        state["workflow_stage"] = stage_number
        state["last_workflow_action"] = f"goto_{stage_number}"
    
    # Get stage info
    stage = WORKFLOW_STAGES[stage_number - 1]
    
    # Build display message
    message = (
        f"🎯 **Jumped to Stage {stage['id']}: {stage['name']}**\n\n"
        f"{stage['icon']} **Description:** {stage['description']}\n\n"
        f"**Recommended Tools:**\n"
    )
    
    for i, tool in enumerate(stage['tools'], 1):
        message += f"{i}. `{tool}`\n"
    
    message += f"\n**Navigation:**\n"
    message += f"• `next_stage()` - Advance to Stage {(stage_number % 14) + 1}\n"
    message += f"• `back_stage()` - Return to Stage {(stage_number - 2) % 14 + 1}\n"
    message += f"• Say 'go to stage N' to jump to any stage\n"
    
    return {
        "status": "success",
        "current_stage": stage_number,
        "stage_name": stage['name'],
        "stage_icon": stage['icon'],
        "tools": stage['tools'],
        "message": message,
        "__display__": message
    }
```

### Step 7: Add Wrapper in `adk_safe_wrappers.py`

**File**: `data_science/adk_safe_wrappers.py`

**Add**:
```python
def goto_stage_tool(stage_number: int, **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for goto_stage."""
    from .ds_tools import goto_stage
    tool_context = kwargs.get("tool_context")
    
    result = _run_async(goto_stage(stage_number=stage_number, tool_context=tool_context))
    return _ensure_ui_display(result, "goto_stage")
```

### Step 8: Register New Tools in Agent

**File**: `data_science/agent.py`  
**Location**: Tool registration section

**Add**:
```python
from .adk_safe_wrappers import (
    # ... existing tools ...
    goto_stage_tool,
)

# Register in agent
llm_agent.add_tool(goto_stage_tool)
```

## Benefits of 14-Stage Workflow

### For Users:
- ✅ **Complete Coverage**: All workflow steps explicitly defined
- ✅ **Clear Prediction Stage**: Dedicated stage for inference (Stage 9)
- ✅ **Separated Reporting**: Executive report vs PDF export are distinct steps
- ✅ **Easy Navigation**: next/back/goto tools for flexible workflow

### For Workflow:
- ✅ **Industry Standard**: Matches professional data science methodology
- ✅ **Sequential**: Natural progression from data → model → predictions → reports
- ✅ **Flexible**: Can jump, skip, or iterate as needed
- ✅ **Comprehensive**: Covers entire ML lifecycle

## Testing Plan

### Test Scenario 1: Complete Linear Workflow
```
1. Upload CSV → Auto Stage 1 (Data Collection)
2. Run next_stage() → Stage 2 (Cleaning)
3. Run next_stage() → Stage 3 (EDA)
4. Run next_stage() → Stage 4 (Visualization)
5. Run next_stage() → Stage 5 (Feature Engineering)
6. Run next_stage() → Stage 6 (Statistical Analysis)
7. Run next_stage() → Stage 7 (Model Training)
8. Run next_stage() → Stage 8 (Evaluation)
9. Run next_stage() → Stage 9 (Prediction) ← NEW!
10. Run next_stage() → Stage 10 (Deployment)
11. Run next_stage() → Stage 11 (Reporting)
12. Run next_stage() → Stage 12 (Others)
13. Run next_stage() → Stage 13 (Executive Report)
14. Run next_stage() → Stage 14 (Export PDF)
```

### Test Scenario 2: Jump Navigation
```
1. User at Stage 3
2. User says "go to stage 9"
3. System should jump to Stage 9 (Prediction & Inference)
4. System shows prediction tools only
```

### Test Scenario 3: Back Navigation
```
1. User at Stage 9
2. Run back_stage() → Should go to Stage 8 (Evaluation)
3. Run back_stage() → Should go to Stage 7 (Model Training)
```

## Migration Notes

### Breaking Changes:
- ⚠️ Existing sessions with `workflow_stage` state may reference old 11-stage system
- ⚠️ Stage IDs 9-11 will shift to 10-12
- ⚠️ Hard-coded stage references in docs will need updating

### Backwards Compatibility:
```python
# Add migration logic in next_stage()
def migrate_old_stage(old_stage_id):
    """Migrate from 11-stage to 14-stage system."""
    if old_stage_id <= 8:
        return old_stage_id  # Stages 1-8 unchanged
    elif old_stage_id == 9:
        return 10  # Old "Deployment" → New "Deployment"
    elif old_stage_id == 10:
        return 11  # Old "Reporting" → New "Reporting"
    elif old_stage_id == 11:
        return 12  # Old "Advanced" → New "Others"
    return old_stage_id
```

## Files to Update

### Core Files:
1. ✅ `data_science/ds_tools.py` - WORKFLOW_STAGES, next_stage(), back_stage(), new goto_stage()
2. ✅ `data_science/adk_safe_wrappers.py` - Add goto_stage_tool wrapper
3. ✅ `data_science/agent.py` - Update system prompt with 14 stages
4. ✅ `data_science/agent.py` - Register goto_stage_tool

### Documentation Files:
5. ✅ `data_science/docs/PROFESSIONAL_WORKFLOW_GUIDE.md` - Update to 14 stages
6. ✅ `data_science/docs/WORKFLOW_NAVIGATION_TOOLS_COMPLETE.md` - Update examples
7. ✅ `data_science/docs/SEQUENTIAL_STAGE_FIX.md` - Update from 11 to 14
8. ✅ Create `data_science/docs/PREDICTION_INFERENCE_STAGE.md` - Document new Stage 9

## Implementation Priority

### Phase 1: Core Workflow (High Priority)
- Update WORKFLOW_STAGES to 14 stages
- Update next_stage() and back_stage() functions
- Add new Stage 9 (Prediction & Inference)

### Phase 2: Navigation Tools (Medium Priority)
- Implement goto_stage() function
- Add goto_stage_tool wrapper
- Register in agent

### Phase 3: Agent Instructions (Medium Priority)
- Update agent system prompt
- Update stage selection logic
- Add examples for new Stage 9

### Phase 4: Documentation (Low Priority)
- Update all workflow documentation
- Create new stage 9 guide
- Update examples and tutorials

## Rollout Strategy

### Option 1: Immediate (Recommended)
Implement all changes in one update:
- ✅ Complete coverage
- ✅ No confusion between versions
- ⚠️ Requires thorough testing

### Option 2: Gradual
Phase 1 → Test → Phase 2 → Test → etc:
- ✅ Lower risk
- ✅ Can validate each phase
- ⚠️ Temporary inconsistency

## Recommendation

**Implement Phase 1 (Core Workflow) immediately**:
1. Update WORKFLOW_STAGES to 14 stages
2. Update next_stage() and back_stage()
3. Basic test with next/back navigation

**Defer Phase 2-4** to future updates:
- goto_stage() is nice-to-have
- Agent prompt updates can be gradual
- Documentation can be updated incrementally

---

**Status**: Implementation plan complete  
**Next Step**: Apply Phase 1 changes when ready  
**Estimated Effort**: 2-3 hours for complete implementation  
**Risk Level**: Medium (affects core workflow logic)

