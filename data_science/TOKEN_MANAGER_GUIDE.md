# Intelligent Token Manager - Usage Guide

## Overview
The `token_manager.py` module provides intelligent token management for LLM calls, preventing "maximum context length exceeded" errors while preserving important information.

## Features
✅ **Accurate Token Counting** - Uses tiktoken for OpenAI models, smart approximation for others  
✅ **Intelligent Truncation** - Preserves structure, headings, and important content  
✅ **Multi-Provider Support** - Works with OpenAI, Gemini, Claude, and custom models  
✅ **Automatic Fixing** - Auto-truncates messages to fit within limits  
✅ **Priority Preservation** - Keeps system prompts and recent messages  
✅ **Smart Strategies** - Multiple truncation strategies (start, end, middle, smart)  
✅ **Easy Integration** - Simple decorator or function call  

## Installation

```bash
# Install tiktoken for accurate token counting (optional but recommended)
pip install tiktoken
```

## Quick Start

### Method 1: Simple Function Wrapper

```python
from token_manager import safe_llm_call

# Your messages
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Very long user query..." * 1000}
]

# Automatically fix if exceeds limit
safe_messages, token_info = safe_llm_call(messages, model="gpt-4o-mini")

print(f"Original: {token_info['total']} tokens")
print(f"Fixed: {token_info.get('fixed_total', token_info['total'])} tokens")

# Use safe_messages for your LLM call
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=safe_messages
)
```

### Method 2: Decorator (Recommended)

```python
from token_manager import ensure_token_limit
from openai import OpenAI

client = OpenAI()

@ensure_token_limit(model="gpt-4o-mini")
def call_gpt(messages, **kwargs):
    """This function is now protected from token limit errors."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        **kwargs
    )

# Use normally - token limits handled automatically
response = call_gpt(messages=[
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Huge query..." * 10000}
])
```

### Method 3: Manual Control

```python
from token_manager import IntelligentTokenManager

# Initialize manager for specific model
manager = IntelligentTokenManager(
    model="gpt-4o-mini",
    reserved_for_response=2000  # Reserve tokens for response
)

# Count tokens
text = "Your long content here..."
tokens = manager.count_tokens(text)
print(f"Token count: {tokens}")

# Truncate if needed
if tokens > 1000:
    truncated = manager.truncate_text(text, max_tokens=1000, strategy="smart")
    print(f"Truncated to: {manager.count_tokens(truncated)} tokens")

# Validate chat messages
messages = [...]
safe_messages = manager.validate_and_fix(messages)
```

## Supported Models

### OpenAI
- `gpt-4` (8K)
- `gpt-4-32k` (32K)
- `gpt-4-turbo` (128K)
- `gpt-4o` (128K)
- `gpt-4o-mini` (128K)
- `gpt-3.5-turbo` (16K)

### Google Gemini
- `gemini-pro` (32K)
- `gemini-1.5-pro` (1M)
- `gemini-1.5-flash` (1M)
- `gemini-2.0-flash` (1M)

### Anthropic Claude
- `claude-3-opus` (200K)
- `claude-3-sonnet` (200K)
- `claude-3-haiku` (200K)

### Others
- `llama-2-70b` (4K)
- `mixtral-8x7b` (32K)

*Note: Automatically detects model from partial names (e.g., "gpt-4-0125-preview" → "gpt-4")*

## Truncation Strategies

### 1. **Start** - Keep Beginning
```python
truncated = manager.truncate_text(text, 500, strategy="start")
# Output: "First 500 tokens... [content truncated]"
```
**Use when:** First part contains most important info (e.g., instructions, setup)

### 2. **End** - Keep Ending
```python
truncated = manager.truncate_text(text, 500, strategy="end")
# Output: "[content truncated] ...last 500 tokens"
```
**Use when:** Latest information is most relevant (e.g., recent logs, last results)

### 3. **Middle** - Keep Both Ends
```python
truncated = manager.truncate_text(text, 500, strategy="middle")
# Output: "First 250... [middle truncated] ...last 250"
```
**Use when:** Both beginning and end are important (e.g., setup + results)

### 4. **Smart** - Preserve Structure (Recommended)
```python
truncated = manager.truncate_text(text, 500, strategy="smart")
# Preserves:
# - Headings (# ## ###)
# - Code blocks (```...```)
# - First/last paragraphs
# - Important markers
```
**Use when:** Content has structure (e.g., markdown, documentation, reports)

## Advanced Usage

### Preparing Structured Prompts

```python
manager = IntelligentTokenManager(model="gpt-4o-mini")

# Automatically allocates token budget across components
formatted_prompt, breakdown = manager.prepare_prompt(
    system="You are a data science expert.",
    user="Analyze this dataset and provide insights.",
    context="Dataset contains 10,000 rows of customer data...",
    examples=[
        "Example 1: Customer churn analysis...",
        "Example 2: Revenue prediction..."
    ]
)

print(f"Token breakdown: {breakdown}")
# {
#   'system': 12,
#   'user': 15,
#   'context': 450,
#   'examples': 200,
#   'total': 677,
#   'available': 126900,
#   'reserved_for_response': 1000
# }
```

### Fitting Different Content Types

```python
# Fit a string
text = "Very long text..." * 1000
fitted_text = manager.fit_content(text, priority="recent")

# Fit a list (keeps most recent)
items = ["Item 1", "Item 2", ..., "Item 1000"]
fitted_list = manager.fit_content(items, priority="recent")

# Fit a dictionary (keeps important keys)
data = {
    "instruction": "Do this...",
    "context": "Large context...",
    "examples": "Many examples..."
}
fitted_dict = manager.fit_content(data, priority="important")
```

### Chat Message Validation

```python
# Automatically truncates old messages, keeps recent + system
messages = [
    {"role": "system", "content": "System prompt"},
    {"role": "user", "content": "Message 1"},
    {"role": "assistant", "content": "Response 1"},
    # ... many more messages ...
    {"role": "user", "content": "Latest message"}
]

# Validates and fixes
safe_messages = manager.validate_and_fix(messages)

# Always keeps:
# 1. System message (truncated if needed)
# 2. Most recent user/assistant messages
# 3. Fits within token limit
```

## Integration with Existing Code

### Before (Risk of Token Limit Errors)
```python
def analyze_with_ai(data_summary, user_query):
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": f"Data: {data_summary}\n\nQuery: {user_query}"}
    ]
    
    # ⚠️ May exceed token limit if data_summary is large
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
```

### After (Protected)
```python
from token_manager import IntelligentTokenManager

def analyze_with_ai(data_summary, user_query):
    manager = IntelligentTokenManager(model="gpt-4o-mini")
    
    # Prepare prompt with automatic token management
    prompt, _ = manager.prepare_prompt(
        system=get_system_prompt(),
        user=user_query,
        context=data_summary
    )
    
    messages = [
        {"role": "system", "content": prompt}
    ]
    
    # ✅ Guaranteed to fit within token limit
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
```

## Configuration Examples

### Conservative (More Room for Response)
```python
manager = IntelligentTokenManager(
    model="gpt-4o-mini",
    reserved_for_response=4000  # Reserve 4K tokens for response
)
# Available for prompt: 124,000 tokens (out of 128K)
```

### Aggressive (Maximum Prompt Size)
```python
manager = IntelligentTokenManager(
    model="gpt-4o-mini",
    reserved_for_response=500  # Minimal response space
)
# Available for prompt: 127,400 tokens
```

### Custom Model
```python
# Add custom model support
from token_manager import MODEL_TOKEN_LIMITS

MODEL_TOKEN_LIMITS["my-custom-model"] = 16000

manager = IntelligentTokenManager(model="my-custom-model")
```

## Best Practices

### 1. **Use Early in Pipeline**
```python
# ✅ Good: Validate before building messages
content = manager.fit_content(large_context)
messages = build_messages(content)

# ❌ Bad: Validate after messages are built
messages = build_messages(large_context)
safe_messages = manager.validate_and_fix(messages)  # May lose important parts
```

### 2. **Choose Right Strategy**
```python
# For structured content (reports, markdown)
manager.truncate_text(report, 1000, strategy="smart")

# For logs/traces
manager.truncate_text(logs, 1000, strategy="end")

# For instructions
manager.truncate_text(instructions, 1000, strategy="start")
```

### 3. **Monitor Token Usage**
```python
_, token_info = safe_llm_call(messages, model="gpt-4o-mini")

if token_info["exceeds"]:
    logger.warning(f"Had to truncate: {token_info['total']} -> {token_info['fixed_total']}")
```

### 4. **Reserve Adequate Response Tokens**
```python
# For short answers (100-500 tokens)
manager = IntelligentTokenManager(reserved_for_response=1000)

# For long responses (code, reports)
manager = IntelligentTokenManager(reserved_for_response=4000)

# For complete documents
manager = IntelligentTokenManager(reserved_for_response=10000)
```

## Error Handling

```python
from token_manager import safe_llm_call

try:
    # With auto_fix=False, raises error if exceeds
    messages, info = safe_llm_call(messages, model="gpt-4o-mini", auto_fix=False)
except ValueError as e:
    print(f"Token limit exceeded: {e}")
    # Handle manually
```

## Performance Notes

### Token Counting Speed
- **With tiktoken:** ~1-2ms for 1000 tokens (accurate)
- **Without tiktoken:** ~0.1ms for 1000 tokens (approximation)

### Caching
- Tokenizer is loaded once per manager instance
- Use global `get_token_manager()` for reuse

```python
from token_manager import get_token_manager

# Reuses same manager instance
manager1 = get_token_manager("gpt-4o-mini")
manager2 = get_token_manager("gpt-4o-mini")  # Same instance
assert manager1 is manager2
```

## Logging

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.INFO)

# You'll see:
# [TOKEN MANAGER] Initialized for gpt-4o-mini: 128000 max tokens
# [TOKEN MANAGER] Prompt prepared: 1234/126900 tokens used
# [TOKEN MANAGER] Messages exceed limit: 130000/126900 tokens, truncating...
```

## Testing

```python
def test_token_manager():
    manager = IntelligentTokenManager(model="gpt-4o-mini")
    
    # Test counting
    assert manager.count_tokens("Hello world") > 0
    
    # Test truncation
    long_text = "x" * 10000
    truncated = manager.truncate_text(long_text, max_tokens=100)
    assert manager.count_tokens(truncated) <= 100
    
    # Test message validation
    huge_messages = [
        {"role": "system", "content": "x" * 1000000}
    ]
    safe = manager.validate_and_fix(huge_messages)
    assert manager.count_messages_tokens(safe) <= manager.budget.available_for_prompt
    
    print("✓ All tests passed")

test_token_manager()
```

## Troubleshooting

### Issue: "tiktoken not available"
**Solution:** Install tiktoken: `pip install tiktoken`  
**Impact:** Falls back to approximation (slightly less accurate)

### Issue: Token count still slightly off
**Reason:** Different models use different tokenizers  
**Solution:** Results are conservative - you'll always have buffer space

### Issue: Important content being truncated
**Solution:** Use `strategy="smart"` or increase `reserved_for_response`

### Issue: Messages still exceed limit
**Reason:** System prompt too large  
**Solution:** Reduce system prompt or use higher token limit model

## Summary

The Intelligent Token Manager provides a robust, easy-to-use solution for preventing token limit errors in LLM applications. Key benefits:

- ✅ **Zero configuration** - Works out of the box
- ✅ **Intelligent** - Preserves important content
- ✅ **Flexible** - Multiple strategies and options
- ✅ **Production-ready** - Comprehensive logging and error handling
- ✅ **Fast** - Minimal overhead with caching

**Recommended approach:** Use the `@ensure_token_limit` decorator for automatic protection with zero code changes to existing LLM calls.

