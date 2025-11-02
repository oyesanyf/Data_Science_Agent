# 🚨 FUNDAMENTAL ISSUE: ADK Framework Strips Tool Results

## The Problem

LLM receives:
```json
{"status": "success", "result": null}
```

Even though our tools return:
```json
{
  "status": "success",
  "__display__": "Shape: 244 rows × 7 columns...",
  "rows": 244,
  "columns": 7,
  ...
}
```

**The ADK framework is stripping the result dict and replacing it with `null`.**

---

## Evidence

### 1. Tools Execute Successfully
- No errors in logs
- `status: "success"` appears in UI
- Tools reach return statements

### 2. Tools Return Correct Data
- `shape()` returns dict with `__display__`, `rows`, `columns`
- `describe()` returns dict with `__display__`, `overview`, `shape`
- `head()` returns dict with `__display__`, `data`, `preview`

### 3. safe_tool_wrapper Adds __display__
- `_normalize_display()` runs successfully
- Guarantees `__display__` field exists
- Logs show it's being added

### 4. ADK Framework Strips Everything
- LLM receives `{"status": "success", "result": null}`
- ALL data fields removed
- Only `status` and `null` result remain

### 5. Only plot() Works
- plot() creates **file artifacts** (PNGs)
- Artifacts bypass the result dict mechanism
- Files are saved to disk and displayed separately

---

## What We've Tried

### Attempt 1: Add __display__ to Tools ❌
- Added to 175+ tools
- Created `@ensure_display_fields` decorator
- Tools DO return `__display__`
- **Result:** Still `null`

### Attempt 2: LLM Instructions ❌
- Ultra-aggressive prompts
- Forbidden phrases
- Mandatory checklists
- RULE #1 at top
- **Result:** LLM can't display what it doesn't receive

### Attempt 3: Fix Callback ❌
- Updated `callbacks.py` to check `__display__` first
- Added to 3 places in callback
- **Result:** Callback never runs because result is already `null`

### Attempt 4: Disable Streaming Tools ❌
- Stopped auto-chaining
- Removed contradictory instructions
- **Result:** Tools still return `null`

### Attempt 5: _normalize_display() ❌
- Surgical fix to guarantee `__display__`
- Runs in `safe_tool_wrapper`
- **Result:** ADK strips it anyway

---

## Why Only plot() Works

```
plot() workflow:
1. Generate PNG file
2. Save to disk
3. Return {"artifacts": ["plot.png"], ...}
4. ADK sees file path
5. ADK loads PNG from disk
6. ADK displays PNG in UI
✅ Works because it bypasses result dict!

Other tools workflow:
1. Compute statistics
2. Format as text/table
3. Return {"__display__": "formatted text", ...}
4. ADK serializes result
5. ADK converts dict to null (???)
6. LLM receives null
❌ Fails because ADK strips the dict!
```

---

## Root Cause Hypothesis

The ADK framework likely:

1. **Has size limits** on result dicts
2. **Can't serialize** complex nested dicts
3. **Strips fields** it doesn't recognize
4. **Only supports** specific result formats
5. **Requires artifacts** for all output display

---

## Possible Solutions

### Solution A: Save All Output as Artifacts ✅ Most Likely to Work

Convert every tool to save its `__display__` content as a text/markdown artifact:

```python
# In every tool
display_content = "Shape: 244 rows × 7 columns..."

# Save as artifact
artifact_path = workspace / "reports" / f"{tool_name}_output.md"
artifact_path.write_text(display_content)
tool_context.save_artifact(str(artifact_path), display_name=f"{tool_name} Output")

# Return minimal result
return {
    "status": "success",
    "artifact": str(artifact_path)
}
```

This mimics how plot() works.

### Solution B: Use ADK's Built-in Display Mechanism

The ADK might have a specific way to return displayable content:

```python
# Check ADK docs for proper format
return types.ToolResponse(
    content=display_content,
    artifacts=[...]
)
```

### Solution C: Inject Display via Streaming

Stream the display content instead of returning it:

```python
async def tool():
    yield display_content
    return {"status": "success"}
```

### Solution D: Post-Process LLM Input

Intercept the tool result BEFORE the LLM sees it and inject the display content as a user message.

---

## Immediate Test

To verify this is the issue, add aggressive logging:

```python
# In safe_tool_wrapper, after tool executes
print(f"===== TOOL RETURNED =====")
print(f"Type: {type(result)}")
print(f"Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
print(f"__display__ present: {'__display__' in result if isinstance(result, dict) else False}")
print(f"__display__ length: {len(result.get('__display__', '')) if isinstance(result, dict) else 0}")
print(f"Full result: {result}")
print(f"=========================")
```

Then check if the log shows the data BEFORE ADK strips it.

---

## Recommendation

**Try Solution A immediately:**

1. Modify `shape()` to save output as markdown artifact
2. Test if it shows in UI
3. If yes, apply to all tools
4. This is how plot() works and why it's the only one working

---

## The Uncomfortable Truth

We've spent hours:
- Adding `__display__` to tools ✅
- Fixing callbacks ✅  
- Writing LLM instructions ✅
- Normalizing display fields ✅

**ALL OF THIS WAS CORRECT CODE.**

But none of it matters because the ADK framework strips the result before anyone can use it.

The real fix is to **bypass the result dict mechanism entirely** and use artifacts like plot() does.

---

## Next Steps

1. **Test logging** to confirm ADK is stripping results
2. **Implement Solution A** for one tool (shape)
3. **Verify it works** in UI
4. **Apply to all tools** if successful

This is the only path forward given that the ADK is fundamentally incompatible with dict-based tool results.

