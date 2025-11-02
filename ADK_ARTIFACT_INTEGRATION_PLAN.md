# ADK Artifact Integration Plan

## Issue
Currently models are saved primarily to disk, with inconsistent/optional saving to ADK artifact system.

## ADK Best Practice (from documentation)
- **PRIMARY**: Use `context.save_artifact(filename, Part)` - managed by ArtifactService
- **BENEFITS**: 
  - Versioning (automatic version numbers)
  - Persistence (InMemory for dev, GCS for production)
  - Access control
  - Proper MIME types
  - Integration with ADK's artifact loading tools

## Current State

### Tools that save to ADK artifacts ✅
- `baseline_model` (line 1524-1528 in ds_tools.py)
- `train_classifier` (line 2817-2818)
- `train_regressor` (line 2865-2866)

### Tools that ONLY save to disk ❌
- `train_decision_tree` (line 3039)
- `train_knn` (line 3375)
- `train_naive_bayes` (line 3460)
- `train_svm` (line 3550)
- **Plus many more** in autosklearn, autogluon, xgboost, etc.

## Recommended Solution

### Phase 1: Create Helper Function
```python
async def save_model_to_artifacts(
    tool_context,
    model_object,
    model_name: str,
    model_type: str,
    target: str,
    metrics: dict,
    metadata: dict = None
) -> dict:
    """
    Universal model saver - saves to ADK artifacts (primary) and disk (backup).
    
    Returns:
        dict with model_path, adk_artifact_name, status
    """
    # 1. Save to ADK artifacts (PRIMARY)
    if tool_context:
        buf = BytesIO()
        joblib.dump(model_object, buf)
        artifact_filename = f"{model_name}.joblib"
        
        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=Part.from_bytes(
                data=buf.getvalue(),
                mime_type="application/octet-stream"
            )
        )
    
    # 2. Save to disk (BACKUP/DEBUG)
    model_dir = Path(workspace) / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    disk_path = model_dir / f"{model_name}.joblib"
    joblib.dump(model_object, disk_path)
    
    # 3. Register in global registry
    from .model_registry import register_model
    register_model(
        model_name=model_name,
        model_path=str(disk_path),  # Backup path
        adk_artifact_name=artifact_filename,  # PRIMARY reference
        model_type=model_type,
        target=target,
        metrics=metrics,
        tool_context=tool_context
    )
    
    return {
        "model_path": str(disk_path),  # For backward compatibility
        "adk_artifact": artifact_filename,  # ADK reference
        "version": version,
        "status": "success"
    }
```

### Phase 2: Update All Training Tools
Replace disk-only saves with:
```python
# OLD (disk only):
joblib.dump(model, model_path)

# NEW (ADK + disk):
await save_model_to_artifacts(
    tool_context=tool_context,
    model_object=model,
    model_name=f"{model_type}_{target}",
    model_type="RandomForest",
    target=target,
    metrics=metrics
)
```

### Phase 3: Update Model Loading Tools
Tools like `accuracy`, `evaluate`, `predict` should:
```python
async def accuracy_tool(model_name: str = "", tool_context=None, **kwargs):
    # Try ADK artifacts FIRST
    if tool_context:
        artifact = await tool_context.load_artifact(filename=f"{model_name}.joblib")
        if artifact and artifact.inline_data:
            model = joblib.loads(artifact.inline_data.data)
    
    # Fallback to disk if needed
    if not model:
        model = joblib.load(disk_path)
```

## Benefits of This Approach

1. **ADK Native**: Uses ADK's built-in artifact system properly
2. **Production Ready**: Works with GcsArtifactService for cloud deployment
3. **Versioning**: Automatic version tracking
4. **Backward Compatible**: Still saves to disk as backup
5. **LLM Accessible**: Models visible to LLM via `load_artifacts_tool`

## Implementation Priority

### High Priority (Core ML Tools)
- [ ] `train_classifier` - Fix to ensure ADK save
- [ ] `train_regressor` - Fix to ensure ADK save  
- [ ] `train_decision_tree` - Add ADK save
- [ ] `train_knn` - Add ADK save
- [ ] `train_naive_bayes` - Add ADK save
- [ ] `train_svm` - Add ADK save

### Medium Priority (AutoML)
- [ ] `auto_sklearn_classify`
- [ ] `auto_sklearn_regress`
- [ ] `autogluon_train_classifier`
- [ ] `autogluon_train_regressor`

### Low Priority (Specialized)
- [ ] XGBoost tools
- [ ] Neural network tools
- [ ] Ensemble tools

## Testing Plan

1. Train model → Verify saved to ADK artifacts
2. List artifacts → Should show `{model_name}.joblib`
3. Load model from artifacts → Should work
4. Registry shows `adk_artifact_saved: true`
5. GCS integration test (if configured)

---

**Status**: Ready for implementation
**Estimated Effort**: 2-3 hours to update all ~20 training tools
**Risk**: Low (backward compatible with disk storage)

