# LiteLlm CSV Upload Fix

## Problem

When using OpenAI models via LiteLlm, uploading CSV files through the web interface caused this error:

```
ERROR: LiteLlm(BaseLlm) does not support this content part.
ValueError: LiteLlm(BaseLlm) does not support this content part.
```

## Root Cause

**LiteLlm only supports these inline_data mime types:**
- `image/*` (images)
- `video/*` (videos)  
- `application/pdf` (PDFs)

**CSV files are NOT supported** because they use mime types like:
- `text/csv`
- `application/csv`
- `text/plain`
- `application/octet-stream`

When the ADK web UI uploads a CSV file, it sends it as `inline_data` in the message. LiteLlm's `_get_content()` function (line 283 in `lite_llm.py`) throws an error for unsupported mime types.

## Solution

Added a `before_model_callback` that intercepts messages with CSV/text files **before** they reach LiteLlm:

### How It Works:

1. **Intercept**: Callback runs before each LLM call
2. **Detect**: Check if message contains `inline_data` with CSV/text mime types
3. **Save**: Save the file to `.data/` directory with timestamp filename
4. **Replace**: Replace `inline_data` with a text message describing the file
5. **Continue**: Let LiteLlm process the modified message (now text-only)

### Code Location:

File: `data_science/agent.py`

```python
def _handle_file_uploads_callback(
    callback_context: CallbackContext, 
    llm_request: LlmRequest
) -> Optional[None]:
    """Handle CSV/text file uploads by saving them to .data directory."""
    # ... implementation ...

root_agent = LlmAgent(
    # ... other config ...
    before_model_callback=_handle_file_uploads_callback,
)
```

## What Happens Now:

### Before (Error):
```
User uploads file.csv
→ ADK sends inline_data with mime_type='text/csv'
→ LiteLlm: ❌ ValueError: does not support this content part
```

### After (Fixed):
```
User uploads file.csv
→ Callback intercepts message
→ Saves to: .data/uploaded_1234567890.csv
→ Replaces inline_data with text:
   "[File uploaded: uploaded_1234567890.csv]
    File saved to: C:\...\data_science\.data\uploaded_1234567890.csv
    Size: 1234 bytes
    Type: text/csv"
→ LiteLlm: ✅ Processes text message successfully
→ Agent sees file path and can use list_data_files() to access it
```

## Supported File Types:

### ✅ Automatically Handled by Callback:
- CSV files (`text/csv`, `application/csv`)
- Text files (`text/plain`, `text/*`)
- Generic binary files (`application/octet-stream`)

### ✅ Natively Supported by LiteLlm:
- Images (`image/png`, `image/jpeg`, etc.)
- Videos (`video/mp4`, `video/mpeg`, etc.)
- PDFs (`application/pdf`)

## Benefits:

1. ✅ **CSV uploads work** through web UI
2. ✅ **No error messages** for unsupported types
3. ✅ **Files automatically saved** to `.data/` directory
4. ✅ **Agent knows file paths** and can use tools
5. ✅ **Images/videos/PDFs still work** natively with LiteLlm
6. ✅ **Backward compatible** - doesn't break existing functionality

## Testing:

1. Start the agent: `.\start_with_openai.ps1`
2. Open web UI: http://localhost:8080
3. Upload a CSV file through the chat interface
4. ✅ File should be saved to `.data/` directory
5. ✅ Agent should respond with file details
6. ✅ Agent can use `list_data_files()` to see the file
7. ✅ Agent can run AutoML on the uploaded data

## Alternative Approaches Considered:

1. ❌ **Modify LiteLlm source** - Would require forking/patching
2. ❌ **Convert CSV to base64 text** - Would exceed token limits
3. ❌ **Disable file uploads** - Would break user experience
4. ✅ **Use before_model_callback** - Clean, non-invasive solution

## Related Files:

- `data_science/agent.py` - Main fix implementation
- `data_science/ds_tools.py` - Contains `list_data_files()` tool
- `.venv/Lib/site-packages/google/adk/models/lite_llm.py` - LiteLlm source (line 283)

## References:

- Google ADK Documentation: Callbacks
- LiteLLM GitHub: https://github.com/BerriAI/litellm
- ADK before_model_callback API: https://adk.google/docs/callbacks

---

**Status:** ✅ Fixed and deployed  
**Version:** 2025-10-15  
**Author:** AI Assistant

