# 🚨 CRITICAL: ADK Showing result: null

## The Problem

User shows describe() in the UI trace:
```
result: null
status: "success"
```

But no errors in logs! This means:
1. ✅ Tool executed successfully
2. ✅ Tool returned a result dict with `__display__`
3. ❌ **ADK framework shows `null` instead of the result**

## Why Only plot() Works

plot() creates **artifacts** (PNG images) that get saved to disk and displayed in the UI.
Other tools return **dict results** that the ADK might not be displaying.

## Root Cause Hypothesis

**The ADK framework might only display:**
- ✅ Artifacts (files saved via `save_artifact()`)
- ❌ NOT dict results (even with `__display__`)

This would explain:
- plot() works → Creates PNG artifacts
- describe(), head(), stats() don't show → Return dict results

## Solution: Save Display Content as Artifacts

Instead of returning `__display__` in the result dict, we need to:

1. Create a markdown/text artifact
2. Save it via `tool_context.save_artifact()`
3. Return artifact reference

This is how plot() works - it saves PNG files and they show up in the UI.

## Test This Hypothesis

Check the ADK documentation or code to see if:
- `result` dicts are displayed in the UI
- Or only `artifacts` are displayed

If only artifacts are displayed, we need to modify ALL tools to save their `__display__` content as text artifacts.

## Quick Fix to Test

Modify describe_tool_guard to save display as artifact:

```python
# After creating formatted_message
artifact_path = ws / "reports" / f"{tool_name}_output.md"
artifact_path.write_text(formatted_message)
tool_context.save_artifact(str(artifact_path), display_name=f"{tool_name} Output")
```

If this makes describe() show in the UI, then we know ALL tools need this fix.

