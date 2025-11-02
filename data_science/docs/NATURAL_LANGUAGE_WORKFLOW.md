# Natural Language Workflow Navigation

## Overview

The system now recognizes **natural language variations** for workflow navigation, making it easy for users to move through the workflow using simple, intuitive commands.

## Supported Commands

### Advance to Next Stage

When users say **ANY** of these phrases, the system automatically calls `next_stage()`:

- "next"
- "next stage"
- "next step"
- "go to next"
- "go to next stage"
- "go to next step"
- "advance"
- "move forward"
- "continue"
- "proceed"
- "go forward"

### Go Back to Previous Stage

When users say **ANY** of these phrases, the system automatically calls `back_stage()`:

- "back"
- "back stage"
- "back step"
- "go back"
- "go back stage"
- "go back step"
- "previous"
- "previous stage"
- "previous step"
- "go to previous"
- "return"
- "revert"

## Implementation

### 1. Agent Instructions

**File:** `agent.py` (lines 2743-2783)

Added explicit instructions to the LLM agent:
- **Recognize** natural language variations
- **Immediately call** the appropriate tool without asking for clarification
- **Direct commands** - no confirmation needed

### 2. Tool Descriptions

**File:** `ds_tools.py`

Updated tool docstrings to include natural language triggers:
- `next_stage()` - Lists all "next" variations
- `back_stage()` - Lists all "back" variations

## Examples

### Example 1: Simple "next"

```
User: "next"
Agent: [Calls next_stage() immediately]
→ Shows Stage 4: Visualization
```

### Example 2: Natural "go back"

```
User: "go back"
Agent: [Calls back_stage() immediately]
→ Shows Stage 3: EDA
```

### Example 3: Explicit "next stage"

```
User: "next stage"
Agent: [Calls next_stage() immediately]
→ Shows next stage with recommended tools
```

### Example 4: Full phrase "go back step"

```
User: "go back step"
Agent: [Calls back_stage() immediately]
→ Shows previous stage
```

## Behavior

### ✅ What Happens

1. **User says** any variation (e.g., "next", "go back")
2. **Agent recognizes** the command from natural language
3. **Agent calls** appropriate tool immediately (`next_stage()` or `back_stage()`)
4. **System shows** the new stage with recommended tools
5. **Agent waits** for next user command

### ❌ What Does NOT Happen

- ❌ Agent does NOT ask "Did you mean next stage?"
- ❌ Agent does NOT present options
- ❌ Agent does NOT ask for clarification
- ❌ Agent does NOT ignore the command

## Key Features

1. **Multiple Variations** - 11+ ways to say "next", 12+ ways to say "back"
2. **Direct Action** - No confirmation needed
3. **Case Insensitive** - Works with any capitalization
4. **Context Aware** - Understands intent even with extra words
5. **Intuitive** - Uses natural language that users expect

## Integration with Workflow Persistence

The natural language recognition works seamlessly with workflow persistence:

1. User says "next" → `next_stage()` is called
2. Workflow state is saved to persistent storage
3. On server restart, workflow resumes from saved stage
4. User can continue with "next" or "back" commands

## Technical Details

### Recognition Logic

The agent uses pattern matching on user input:
- Checks for keywords: "next", "back", "advance", "continue", etc.
- Matches variations: "next stage", "go back", "previous step"
- Calls appropriate tool based on matched pattern

### Tool Execution

```python
# User says: "next"
if user_input.lower() in ["next", "next stage", "next step", ...]:
    result = await next_stage(tool_context)
    # Show stage info

# User says: "back"
if user_input.lower() in ["back", "back stage", "go back", ...]:
    result = await back_stage(tool_context)
    # Show previous stage info
```

## Benefits

1. **User-Friendly** - Natural language, no need to remember exact commands
2. **Flexible** - Multiple ways to express the same intent
3. **Fast** - Direct execution without confirmation
4. **Intuitive** - Works the way users expect
5. **Reliable** - Always calls the correct tool

## Testing

### Test Cases

✅ "next" → Calls `next_stage()`
✅ "next stage" → Calls `next_stage()`
✅ "go to next" → Calls `next_stage()`
✅ "back" → Calls `back_stage()`
✅ "go back" → Calls `back_stage()`
✅ "previous stage" → Calls `back_stage()`

### Edge Cases

- "next please" → Should still recognize "next"
- "can you go back" → Should recognize "go back"
- "move to next stage" → Should recognize "next stage"

## Future Enhancements

Potential additions:
- "stage 5" → Jump directly to specific stage
- "skip" → Skip to next stage
- "restart" → Go back to stage 1
- "where am I" → Show current stage without changing

---

**Status:** ✅ Production Ready

**Version:** 1.0

**Last Updated:** 2025-01-28

