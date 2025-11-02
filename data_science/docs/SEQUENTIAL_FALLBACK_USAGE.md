# SequentialAgent Fallback Usage Guide

## Overview

The SequentialAgent fallback system provides a **smart, conditional fallback** that only activates when needed. This gives you:

- ✅ **Normal execution** (fast, flexible) by default
- ✅ **SequentialAgent fallback** (guaranteed format) when needed
- ✅ **Best of both worlds** - no unnecessary overhead

## When Fallback Activates

The fallback system activates in these scenarios:

### 1. Explicit User Request
```python
User: "Please use structured output with JSON schema"
# → Fallback activates automatically
```

### 2. Native Support Fails
```python
# If ADK's native output_schema + tools fails
# → Automatically falls back to SequentialAgent
```

### 3. Tool Execution Recovery
```python
# If tool execution fails and needs formatting
# → Uses SequentialAgent to recover
```

## Usage Examples

### Example 1: Basic Fallback Setup

```python
from data_science.sequential_fallback import (
    create_hybrid_agent_with_fallback,
    set_use_sequential_fallback
)
from pydantic import BaseModel

# Define your schema
class ToolResultSchema(BaseModel):
    status: str
    message: str
    metrics: dict

# Create agent with fallback capability
root_agent = create_hybrid_agent_with_fallback(
    base_agent=your_primary_agent,
    output_schema=ToolResultSchema,
    enable_fallback=True
)
```

### Example 2: Conditional Activation

```python
from data_science.structured_output_helper import (
    should_use_sequential_fallback,
    set_use_sequential_fallback
)

# Enable fallback programmatically
set_use_sequential_fallback(True)

# Or check if user requested it
if should_use_sequential_fallback(user_message="use structured output"):
    # Use SequentialAgent
    pass
```

### Example 3: Integration with before_model_callback

```python
from data_science.structured_output_helper import (
    set_structured_output_conditional
)

def combined_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest
):
    # Try native support first
    fallback_info = set_structured_output_conditional(
        callback_context,
        llm_request,
        schema_detection=True,
        check_sequential_fallback=True
    )
    
    if fallback_info and fallback_info.get("use_sequential_fallback"):
        # Switch to SequentialAgent fallback
        logger.info("Using SequentialAgent fallback")
        # ... route to SequentialAgent ...
    
    # Continue with normal processing
    return None
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         User Request                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Check: Structured Output Needed?          │
│  - User keywords detected?                 │
│  - Schema provided?                        │
│  - Tool execution failed?                  │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │              │
        ▼              ▼
   ┌─────────┐   ┌─────────────┐
   │  NO     │   │  YES        │
   │         │   │             │
   │ Normal  │   │ Try Native  │
   │ Agent   │   │ Support     │
   └─────────┘   └──────┬──────┘
                        │
                 ┌──────┴──────┐
                 │              │
                 ▼              ▼
            ┌─────────┐   ┌─────────────┐
            │ SUCCESS │   │  FAILS       │
            │         │   │            │
            │ Use It  │   │ Sequential  │
            └─────────┘   │ Agent       │
                          └─────────────┘
```

## Benefits

1. **Performance**: Normal execution (fast) when possible
2. **Reliability**: SequentialAgent fallback (guaranteed format) when needed
3. **Flexibility**: User can request structured output explicitly
4. **Recovery**: Automatic fallback on failures
5. **No Overhead**: Only creates SequentialAgent when needed

## Configuration

### Enable Fallback Globally

```python
from data_science.structured_output_helper import set_use_sequential_fallback

set_use_sequential_fallback(True)  # Enable fallback
```

### Disable Fallback

```python
set_use_sequential_fallback(False)  # Disable fallback
```

### Check Fallback Status

```python
from data_science.structured_output_helper import should_use_sequential_fallback

if should_use_sequential_fallback(user_message):
    # Use fallback
    pass
```

## When NOT to Use Fallback

- ✅ Normal conversational interactions (default)
- ✅ Simple tool executions
- ✅ When performance is critical
- ✅ When structured output isn't needed

## When TO Use Fallback

- ✅ API integrations requiring strict JSON
- ✅ External system integrations
- ✅ Automated workflows parsing responses
- ✅ Recovery from tool execution failures
- ✅ When user explicitly requests structured output

## Implementation Notes

1. **Lazy Creation**: SequentialAgent is only created when needed
2. **Keyword Detection**: Automatically detects structured output requests
3. **Error Recovery**: Falls back gracefully on failures
4. **Logging**: Comprehensive logging for debugging

## Troubleshooting

### Fallback Not Activating

1. Check if `enable_fallback=True`
2. Verify keywords are detected
3. Check logs for detection messages

### SequentialAgent Import Error

If you see `SequentialAgent not available`, ensure your ADK version supports it:
```python
# Check ADK version
import google.adk
print(google.adk.__version__)  # Should be >= 1.11.0
```

### Schema Conversion Issues

Ensure your Pydantic schema has `model_json_schema()` method:
```python
class MySchema(BaseModel):
    field: str

schema_dict = MySchema.model_json_schema()
```

