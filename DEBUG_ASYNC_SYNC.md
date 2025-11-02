# Debug: Async/Sync Mismatch Check

## Current Call Flow

```
Tool Execution (async)
    ↓
after_tool_callback (async) 
    ↓
_as_blocks(tool_name, result) ← SYNC function called from async
    ↓
publish_ui_blocks (async)
    ↓
clean_for_json(result) ← Called AFTER _as_blocks
```

## Analysis

✅ **No async/sync mismatch found:**
- `_as_blocks` is a **sync function** (line 22)
- `after_tool_callback` is **async** (line 341)
- Calling sync from async is **safe** - no await needed
- `_as_blocks` is called at line 623, BEFORE `clean_for_json` at line 825

## Potential Issues

### 1. Result Structure May Be Different
Tools might return:
- `{"status": "success", "result": {...}}` ← Expected
- `{"status": "success", "overview": {...}}` ← Different structure
- `{"status": "success"}` ← Empty result

### 2. _ensure_ui_display May Have Already Moved Data
- `analyze_dataset_tool` calls `_ensure_ui_display()` at the end
- `_ensure_ui_display()` should extract from `result.result` and set `__display__`
- But if `__display__` is empty/generic, `_as_blocks` should still extract

### 3. Check What Tools Actually Return

**Need to verify:** What does `analyze_dataset` actually return?

Possible structures:
```python
# Structure A (expected):
{
    "status": "success",
    "result": {
        "overview": {...},
        "numeric_summary": {...}
    }
}

# Structure B (different):
{
    "status": "success",
    "overview": {...},
    "numeric_summary": {...}
}

# Structure C (nested differently):
{
    "status": "success",
    "result": null,
    "data": {
        "overview": {...}
    }
}
```

## Action Items

1. ✅ Check logs when running NEW tool - look for `[_as_blocks]` messages
2. ✅ Verify result structure in logs: `nested_result keys: [...]`
3. ✅ Check if `_ensure_ui_display` set `__display__` properly

## Next Steps

Run a NEW tool and check logs:
```
[_as_blocks] Display text is generic, attempting to extract...
[_as_blocks] nested_result keys: ['overview', 'numeric_summary', ...]
[_as_blocks] ✅ SUCCESS: Extracted X data parts...
```

If you see these logs but still get "Debug: Result has keys", then the issue is elsewhere (maybe in how blocks are converted to markdown).

---

**No async/sync mismatch detected** - the code flow is correct.

