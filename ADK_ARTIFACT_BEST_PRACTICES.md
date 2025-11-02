# ADK Artifact System - Best Practices Implementation

Based on the official ADK documentation, here's how we should ensure all artifacts are properly saved and visible in the Session UI.

## Key Insights from Documentation

### 1. **ADK Artifact System**
- Artifacts must be saved as `google.genai.types.Part` objects
- Use `tool_context.save_artifact(filename, artifact_part)` 
- Artifacts are automatically available via `LoadArtifactsTool`
- Artifacts appear in Session UI when saved via ADK service

### 2. **LoadArtifactsTool Pattern**
The `LoadArtifactsTool` works in two steps:
1. **Awareness Phase**: LLM is informed that artifacts exist (e.g., `["notes.txt", "plot.png"]`)
2. **Content Loading**: When LLM requests an artifact, its content is injected into the conversation

### 3. **Session UI Visibility**
Artifacts saved via ADK's `artifact_service.save_artifact()` are automatically visible in:
- Session UI artifacts panel
- Available for `LoadArtifactsTool` awareness
- Accessible via `{artifact.filename}` placeholders

## Current Implementation Status

✅ **Already Implemented:**
1. `load_artifacts` is registered as a tool (agent.py line 4475)
2. `universal_artifact_generator.py` has `save_artifact_via_context()` method
3. Artifacts are saved as `Part` objects with proper MIME types
4. `ensure_artifact_for_tool()` calls `save_artifact_via_context()`

⚠️ **Potential Issues:**
1. `save_artifact_via_context()` might fail silently in some cases
2. Artifacts might only be saved to filesystem, not via ADK service
3. Async/sync handling might not work in all contexts

## Recommended Enhancements

### 1. Ensure Artifacts Are ALWAYS Saved via ADK

**File:** `universal_artifact_generator.py`

**Current Logic:**
```python
# Try to save via ToolContext first
saved_via_context = False
if tool_context:
    saved_via_context = self.save_artifact_via_context(
        tool_context, markdown_content, artifact_name
    )

# Fallback: Save to workspace filesystem
if not saved_via_context and tool_context and hasattr(tool_context, 'state'):
    workspace_root = tool_context.state.get('workspace_root')
    if workspace_root:
        self.save_artifact_to_workspace(...)
```

**Issue:** If `save_artifact_via_context()` fails, we fall back to filesystem, but the Session UI won't see it.

**Recommended Fix:**
```python
# ALWAYS attempt ADK save first (critical for Session UI visibility)
saved_via_context = False
if tool_context and hasattr(tool_context, 'save_artifact'):
    saved_via_context = self.save_artifact_via_context(
        tool_context, markdown_content, artifact_name
    )
    if not saved_via_context:
        logger.warning(f"[ARTIFACT] Failed to save via ADK service - artifact won't appear in Session UI")

# Filesystem save is OK as backup, but ADK save is critical
if workspace_root:
    self.save_artifact_to_workspace(...)  # Keep for local access
```

### 2. Improve Error Handling for Async/Sync

The documentation shows that `save_artifact()` can be async or sync. Our current implementation tries to handle both, but we should be more robust:

```python
# In save_artifact_via_context()
try:
    # Check if async
    if inspect.iscoroutinefunction(tool_context.save_artifact):
        # Handle async with proper event loop management
        # (current implementation is good)
    else:
        # Sync - simple call
        version = tool_context.save_artifact(filename=artifact_name, artifact=artifact_part)
except ValueError as e:
    # Per ADK docs: ValueError if artifact_service not configured
    logger.error(f"[ARTIFACT] ArtifactService not configured: {e}")
    # This is a critical error - ADK service must be configured
    return False
```

### 3. Ensure LoadArtifactsTool Works

The `LoadArtifactsTool` automatically:
- Lists artifacts via `tool_context.list_artifacts()`
- Adds system instructions to LLM requests
- Injects artifact content when LLM requests it

**Verification:**
- ✅ `load_artifacts` is registered as a tool (agent.py line 4475)
- ✅ Agent has access to tool_context in tool wrappers
- ✅ Artifacts are saved with proper names and MIME types

**Test:**
```python
# After running a tool that creates an artifact:
# 1. Check if artifact is in ADK service: tool_context.list_artifacts()
# 2. LLM should be informed: "You have artifacts: ['artifact_name.md']"
# 3. When user asks about it, LLM should call load_artifacts()
```

### 4. Session UI Visibility

For artifacts to appear in Session UI:
1. **Must be saved via ADK service**: `tool_context.save_artifact()`
2. **Proper MIME types**: `text/markdown` for markdown files, `image/png` for images, etc.
3. **Proper Part structure**: `Part(text=...)` for text, `Part(inline_data=Blob(...))` for binary

**Current Implementation:**
```python
# In save_artifact_via_context()
markdown_bytes = markdown_content.encode('utf-8')
artifact_part = types.Part(
    inline_data=types.Blob(
        data=markdown_bytes,
        mime_type="text/markdown"
    )
)
```

✅ **This is correct per ADK documentation!**

## Action Items

1. ✅ **Verify ADK ArtifactService is configured in Runner**
   - Check `main.py` or runner initialization
   - Ensure `artifact_service` parameter is set

2. ✅ **Ensure `save_artifact_via_context()` never fails silently**
   - Add better error logging
   - Return False explicitly on failures

3. ✅ **Test artifact visibility in Session UI**
   - Run a tool that creates markdown artifact
   - Check Session UI artifacts panel
   - Verify artifact appears

4. ✅ **Test LoadArtifactsTool awareness**
   - Run a tool to create an artifact
   - Check if LLM is informed about available artifacts
   - Ask LLM about the artifact - should use `load_artifacts()`

## Summary

Our implementation is **already aligned** with ADK best practices:
- ✅ Using `Part` objects for artifacts
- ✅ Saving via `tool_context.save_artifact()`
- ✅ Using proper MIME types
- ✅ `LoadArtifactsTool` is registered

The fix in `callbacks.py` for extracting nested data is **separate** from artifact saving - it's about displaying results in the Session UI.

**The key is ensuring `save_artifact_via_context()` succeeds**, so artifacts are visible in:
1. Session UI artifacts panel ✅
2. LoadArtifactsTool awareness ✅
3. Filesystem (backup) ✅

---

**Reference:**
- ADK Callbacks Documentation: Shows how artifacts work with ToolContext
- ADK Artifact Management Chapter: Detailed artifact service patterns
- ADK Tools Documentation: Shows LoadArtifactsTool usage

