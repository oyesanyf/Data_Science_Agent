# Comprehensive UI Output & Report Integration System

## Overview
All tool outputs are now automatically captured, displayed in the UI, and included in executive reports with proper organization by workflow section.

## System Architecture

### 1. **UI Display Guarantee** (`adk_safe_wrappers.py`)
Every tool wrapper now uses the universal `_ensure_ui_display()` helper to guarantee UI visibility:

```python
def _ensure_ui_display(result: Any, tool_name: str = "tool") -> Dict[str, Any]:
    """
    Universal helper to ensure ANY tool result has proper UI display fields.
    Priority:
        1. If result already has __display__, keep it
        2. Extract from message/text/ui_text fields
        3. Format based on result type (success, artifacts, metrics)
        4. Fallback to simple success message
    """
```

**Display Fields Added:**
- `__display__` - Primary UI rendering field
- `text`, `message`, `ui_text` - Alternative display fields
- `content`, `display`, `_formatted_output` - Compatibility fields
- `status` - Execution status indicator

### 2. **Automatic Output Persistence** (`callbacks.py`)
The `after_tool_callback()` now automatically saves all tool outputs to workspace:

```python
# ===== SAVE ALL UI OUTPUTS TO WORKSPACE FOR REPORT INCLUSION =====
if isinstance(result, dict) and result.get("__display__"):
    workspace_root = callback_context.state.get("workspace_root")
    if workspace_root:
        reports_dir = Path(workspace_root) / "reports"
        output_file = reports_dir / f"{tool_name}_output_{timestamp}.json"
        
        output_data = {
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "status": result.get("status", "success"),
            "display": result.get("__display__"),
            "data": result,
            "artifacts": result.get("artifacts", []),
            "metrics": result.get("metrics", {})
        }
```

**Saved to:** `workspace_root/reports/{tool_name}_output_{timestamp}.json`

### 3. **Workspace Scanner** (`report_workspace_scanner.py`)
New module that scans the workspace and organizes outputs by workflow section:

**Categories:**
- **EDA**: analyze_dataset, describe, plot, stats, correlation
- **Data Quality**: clean, validate, impute, handle_outliers
- **Feature Engineering**: scale_data, encode, feature_selection, transform
- **Predictions**: predict, forecast, prophet
- **Model Training**: train, hpo, grid_search, automl
- **Model Evaluation**: evaluate, explain, shap
- **Time Series**: arima, sarima, decompose
- **Causal Analysis**: causal_discovery, causal_inference
- **Fairness & Governance**: fairness, bias_detection
- **Drift Monitoring**: drift_detection, data_quality_monitor

**Functions:**
- `collect_workspace_outputs()` - Scans and categorizes all outputs
- `format_output_for_report()` - Formats output for PDF inclusion
- `get_recent_outputs()` - Retrieves recent outputs for a section

### 4. **Dynamic Report Generation** (`ds_tools.py::export_executive_report()`)
Reports now automatically include all workspace outputs organized by section:

```python
# Scan workspace for all outputs
workspace_outputs = collect_workspace_outputs(tool_context=tool_context)

# EDA Section (if outputs found)
if workspace_outputs.get("EDA"):
    elements.append(Paragraph("Exploratory Data Analysis (EDA)", section_style))
    for output in workspace_outputs["EDA"][:5]:
        formatted_text = format_output_for_report(output, "EDA")
        elements.append(Paragraph(formatted_text, body_style))

# Data Quality Section (if outputs found)
if workspace_outputs.get("Data Quality"):
    elements.append(Paragraph("Data Quality & Preprocessing", section_style))
    # ... add outputs

# Feature Engineering Section (if outputs found)
if workspace_outputs.get("Feature Engineering"):
    elements.append(Paragraph("Feature Engineering", section_style))
    # ... add outputs

# Predictions Section (if outputs found) - INCLUDES ALL PREDICTION RESULTS
if workspace_outputs.get("Predictions"):
    elements.append(Paragraph("Prediction Results", section_style))
    for output in workspace_outputs["Predictions"]:  # ALL predictions
        data = output.get("data", {})
        target = data.get("target", "Unknown")
        metrics = data.get("metrics", {})
        # ... format and display metrics
```

## Workflow

### When a Tool Executes:

1. **Tool Execution**
   - Tool runs and returns result (dict/string/any type)

2. **Wrapper Processing** (`adk_safe_wrappers.py`)
   - `_ensure_ui_display()` guarantees all display fields exist
   - Result is converted to standardized dict format

3. **UI Display** (`callbacks.py::_as_blocks()`)
   - Extracts `__display__` field for rendering
   - Publishes to session UI page
   - Persists in SQLite for history

4. **Workspace Persistence** (`callbacks.py::after_tool_callback()`)
   - Saves output as JSON: `{tool_name}_output_{timestamp}.json`
   - Stored in: `workspace_root/reports/`
   - Includes: tool_name, timestamp, status, display, data, artifacts, metrics

### When Report is Generated:

1. **Workspace Scan** (`report_workspace_scanner.py`)
   - Scans `workspace_root/reports/` for all `*_output_*.json` files
   - Maps each tool to appropriate section using `TOOL_SECTIONS` dict
   - Organizes outputs by category (EDA, Predictions, etc.)

2. **Dynamic Section Creation** (`ds_tools.py::export_executive_report()`)
   - Checks each category for available outputs
   - Creates section ONLY if outputs exist
   - Formats and includes all relevant outputs
   - Adds page breaks between sections

3. **PDF Generation**
   - Renders formatted outputs using ReportLab
   - Includes metrics, status, timestamps
   - Maintains clean formatting (removes markdown, emojis)

## Key Features

### ✅ Universal Display Guarantee
- ALL tools display output in UI (no silent failures)
- Automatic fallback formatting if tool doesn't provide display fields
- Consistent format across all tools

### ✅ Automatic Persistence
- No manual saving required
- Outputs survive across sessions
- Timestamped for chronological tracking

### ✅ Smart Categorization
- Tools automatically mapped to appropriate sections
- New sections created dynamically if needed
- Easy to extend with new categories

### ✅ Complete Prediction Integration
- Prediction results ALWAYS included in reports
- Metrics formatted clearly (R², MAE, RMSE, Accuracy, F1)
- Task type identified (classification vs regression)
- ALL predictions included (not truncated)

### ✅ Comprehensive Coverage
- EDA outputs included
- Data quality steps documented
- Feature engineering tracked
- Model training recorded
- Predictions captured
- Evaluation results preserved

## Example: "Predict Price" Workflow

1. **User asks:** "predict price"

2. **Tool Execution:**
   - `predict_tool()` called with target="price"
   - Model trained, predictions generated
   - Metrics calculated (R², MAE, RMSE)

3. **UI Display:**
   - Formatted message with metrics displayed immediately
   - Artifacts listed (model file, prediction JSON)

4. **Workspace Save:**
   - `predict_tool_output_1729783845.json` saved to `workspace_root/reports/`
   - Contains: target, task, metrics, model_path, display text

5. **Report Generation:**
   - Scanner finds prediction output in "Predictions" category
   - Creates "Prediction Results" section
   - Includes:
     - Target: price
     - Task: regression
     - R² Score: 0.856
     - MAE: 12,345.67
     - RMSE: 15,678.90

## Benefits

1. **No Information Loss**: Every tool output is captured and preserved
2. **Better UX**: Users always see results in UI immediately
3. **Professional Reports**: All analysis included with proper organization
4. **Maintainable**: Easy to add new tools/sections without code changes
5. **Debugging**: Failed tools still show status and error info
6. **Audit Trail**: Timestamped outputs provide complete history

## Files Modified

- `data_science/adk_safe_wrappers.py` - Added `_ensure_ui_display()` helper
- `data_science/callbacks.py` - Added automatic workspace saving
- `data_science/ds_tools.py` - Enhanced report generation with dynamic sections
- `data_science/report_workspace_scanner.py` - **NEW** workspace scanning module
- `data_science/streaming_all.py` - Updated streaming outputs for UI display

## Testing Recommendations

1. Run EDA on dataset → check UI display → generate report → verify EDA section
2. Run prediction → check UI display → generate report → verify Predictions section
3. Run multiple tools → check all outputs in UI → verify all in report
4. Test with empty workspace → ensure report handles missing outputs gracefully
5. Test with invalid JSON files → ensure scanner handles errors

## Future Enhancements

- [ ] Add filtering by date range
- [ ] Group related outputs (e.g., all predictions on same target)
- [ ] Add comparison tables for multiple model runs
- [ ] Export workspace outputs to structured CSV/Excel
- [ ] Add search/query functionality for outputs
- [ ] Create visual timeline of analysis steps

