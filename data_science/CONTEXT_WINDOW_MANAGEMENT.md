# Context Window Management

## Overview

This agent includes **intelligent context window management** to handle token limits dynamically and prevent context overflow errors.

## Features

### 1. **Automatic Token Tracking**
- Reads token usage from LLM response headers
- Tracks: `prompt_tokens`, `completion_tokens`, `total_tokens`
- Real-time monitoring with utilization percentages
- Logs warnings when approaching limits

### 2. **Dynamic Tool Reduction**
When context window is exceeded, the system automatically reduces tools:

| Level | Tools | Percentage | Description |
|-------|-------|------------|-------------|
| 0 | 84 tools | 100% | All tools available (default) |
| 1 | ~59 tools | 70% | Core tools (most common workflows) |
| 2 | ~34 tools | 40% | Essential tools only |
| 3 | ~17 tools | 20% | Minimal tools (critical operations) |

### 3. **Intelligent Error Handling**
- Detects context window exceeded errors automatically
- Parses token breakdown: `messages` vs `functions`
- Recommends appropriate action:
  - **Reduce tools** if function definitions are the problem
  - **Clear history** if message history is the problem

### 4. **Proactive Throttling**
- Monitors token usage in real-time
- Warns at 85% utilization (configurable)
- Prevents reaching hard limits

---

## Configuration

### Environment Variables

```bash
# Maximum context tokens (default: 128000 for gpt-4o-mini)
export MAX_CONTEXT_TOKENS=128000

# Safety margin (use only 85% of max to leave buffer)
export CONTEXT_SAFETY_MARGIN=0.85
```

### Model-Specific Limits

| Model | Max Tokens | Recommended Safety Margin |
|-------|------------|---------------------------|
| gpt-4o-mini | 128,000 | 0.85 (108,800 safe limit) |
| gpt-4o | 128,000 | 0.85 (108,800 safe limit) |
| gpt-3.5-turbo | 16,385 | 0.80 (13,108 safe limit) |
| gemini-2.0-flash-exp | 1,048,576 | 0.90 (943,718 safe limit) |

---

## How It Works

### Token Tracking Flow

```
1. User sends message
   ↓
2. Agent processes with LLM
   ↓
3. Response headers read:
   - x-openai-prompt-tokens
   - x-openai-completion-tokens
   - x-openai-total-tokens
   ↓
4. ContextWindowManager tracks usage
   ↓
5. If > 85% → Warning logged
   If > 100% → Error caught
```

### Error Handling Flow

```
Context Window Exceeded Error
   ↓
1. Parse error message:
   - Total tokens
   - Message tokens
   - Function tokens
   ↓
2. Analyze breakdown:
   - Functions > Messages? → Reduce tools
   - Messages > Functions? → Clear history
   ↓
3. Take action:
   - Level 0→1: Remove 30% of tools (advanced features)
   - Level 1→2: Keep only essential (40%)
   - Level 2→3: Minimal set (20%)
   ↓
4. Retry request with reduced context
```

---

## Tool Reduction Strategy

### Level 0: All Tools (84 total)
**Use case:** Normal operation, plenty of tokens available

Includes all 9 workflow stages:
- 🧹 Data Cleaning & Preparation
- 📊 Exploratory Data Analysis
- 📈 Visualization
- ⚙️ Feature Engineering
- 📉 Statistical Analysis
- 🤖 Machine Learning
- 📝 Report and Insights
- 🚀 Production & Monitoring
- 📂 Unstructured Data

### Level 1: Core Tools (~70%)
**Use case:** Moderate token pressure

Removes advanced/specialized tools:
- ❌ Advanced fairness tools
- ❌ Causal inference
- ❌ Deep learning tools
- ❌ Production monitoring
- ❌ Unstructured data processing
- ✅ Keeps core ML workflow

### Level 2: Essential Tools (~40%)
**Use case:** High token pressure

Keeps only critical operations:
- ✅ Data cleaning (robust_auto_clean_file, auto_clean_data)
- ✅ Analysis (describe, plot, stats)
- ✅ ML training (train_classifier, train_regressor, smart_autogluon_automl)
- ✅ Evaluation (evaluate, explain_model)
- ✅ Reporting (export_executive_report)

### Level 3: Minimal Tools (~20%)
**Use case:** Extreme token pressure

Bare minimum for basic workflows:
- describe
- robust_auto_clean_file
- plot
- recommend_model
- train_classifier / train_regressor
- smart_autogluon_automl
- explain_model
- export_executive_report
- help

---

## Example Error & Resolution

### Error Message
```json
{
  "error": "ContextWindowExceededError: This model's maximum context length is 128000 tokens. 
   However, your messages resulted in 140199 tokens 
   (129951 in the messages, 10248 in the functions)."
}
```

### What Happens

1. **Error Detection:**
   ```python
   🔴 Context window exceeded!
   📊 Token breakdown:
     Total: 140,199 tokens
     Messages: 129,951 (92.7%)
     Functions: 10,248 (7.3%)
   ```

2. **Analysis:**
   - Messages > Functions → Message history is the problem
   - Recommendation: Clear conversation history

3. **Action Taken:**
   ```
   💬 Context window exceeded (140,199/128,000 tokens).
   Message history uses 129,951 tokens (92.7%).
   Consider clearing conversation history or summarizing previous context.
   ```

### Alternative Scenario

If `Functions: 75,000 tokens` (higher than messages):
```
🔧 Context window exceeded (140,199/128,000 tokens).
Function definitions use 75,000 tokens (53.5%).
Reducing tool count to level 1...
```

Then retry with only 70% of tools (~59 tools instead of 84).

---

## Best Practices

### 1. **Monitor Token Usage**
```python
# Check logs for token tracking
📊 Token usage: 95,000 / 128,000 (74.2% of limit)
```

### 2. **Clear History Periodically**
After long conversations or complex workflows:
- Start new conversation
- Or use summarization if available

### 3. **Use Appropriate Models**
- **Short tasks:** gpt-4o-mini (128K)
- **Long conversations:** gemini-2.0-flash-exp (1M tokens)

### 4. **Optimize Tool Usage**
- Use `help(command='specific_tool')` instead of `help()` in long conversations
- Request specific tools when you know what you need

### 5. **Environment Configuration**
For very long conversations:
```bash
# Use higher safety margin
export CONTEXT_SAFETY_MARGIN=0.75  # Warn at 75% instead of 85%

# Or switch to larger context model
export OPENAI_MODEL=gpt-4o  # Same 128K but better quality
# OR
export USE_GEMINI=true
export GENAI_MODEL=gemini-2.0-flash-exp  # 1M tokens!
```

---

## Troubleshooting

### "Context window exceeded" persists after tool reduction

**Cause:** Message history is too large  
**Solution:** Clear conversation history and start fresh

### Token tracking not working

**Check:**
1. Response headers are being captured
2. LiteLLM version supports header passthrough
3. Check logs for `Could not track tokens from headers` warnings

### Tools missing after automatic reduction

**Expected behavior!** Check logs for:
```
🔧 Reduced to CORE tools: 59/84 tools (70%)
```

To restore all tools, start a new conversation or clear history.

---

## Technical Details

### Implementation

Located in: `agent.py`

**Classes:**
- `ContextWindowManager`: Main manager class
  - `track_tokens()`: Read headers and track usage
  - `get_tool_subset()`: Filter tools by level
  - `handle_context_overflow()`: Analyze and recommend actions

**Global Instance:**
```python
_context_manager = ContextWindowManager(
    max_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "128000")),
    safety_margin=float(os.getenv("CONTEXT_SAFETY_MARGIN", "0.85"))
)
```

### Header Reading

OpenAI response headers:
- `x-openai-prompt-tokens`
- `x-openai-completion-tokens`  
- `x-openai-total-tokens`

Fallbacks:
- `x-prompt-tokens`
- `x-completion-tokens`
- `x-total-tokens`

### Error Pattern Matching

Detects context errors via keywords:
```python
["context", "window", "exceeded", 
 "maximum context length", 
 "contextwindowexceedederror"]
```

Parses token breakdown:
```regex
(\d+)\s+tokens.*?(\d+)\s+in the messages.*?(\d+)\s+in the functions
```

---

## Future Enhancements

- [ ] Automatic message history summarization
- [ ] Per-tool token cost estimation
- [ ] Smart tool recommendations based on context budget
- [ ] Context-aware tool ordering (priority tools first)
- [ ] Streaming support for partial responses
- [ ] Token prediction before API call

---

## Support

If you encounter context window issues:

1. Check logs for token breakdown
2. Try increasing `CONTEXT_SAFETY_MARGIN`
3. Use `help(command='tool')` for specific tools
4. Consider switching to Gemini for very long conversations
5. Report issues with full error message and token counts

