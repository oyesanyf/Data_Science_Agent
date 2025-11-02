# Critical Bugs Found - October 22, 2025

## Summary
Tools execute successfully but the LLM doesn't see the output. Multiple issues in the data flow pipeline.

## Issues Identified

### 1. ⚠️ Guard Logs Missing from agent.log
**Symptom**: Guard detailed logs (`[HEAD GUARD]`, `[DESCRIBE GUARD]`) don't appear in `agent.log`  
**Impact**: Cannot debug guard execution  
**Root Cause**: Logger configuration or level issue for `head_describe_guard` module  
**Evidence**:
```
# Only startup messages in agent.log, no execution logs
2025-10-22 20:16:35 - agent - INFO - DATA SCIENCE AGENT STARTING
```

### 2. 🐛 list_unstructured_tool Called for CSV Files
**Symptom**: `list_unstructured_tool` executes after CSV analysis  
**Impact**: Confuses LLM, suggests data is unstructured when it's not  
**Root Cause**: Router or agent logic calling unstructured tools inappropriately  
**Evidence**:
```
2025-10-22 20:17:59 - tools - INFO - Executing tool: list_unstructured_tool
2025-10-22 20:17:59 - tools - INFO - [SUCCESS] list_unstructured_tool
```

### 3. ❌ MIME Types Wrong in UI
**Symptom**: Artifacts show as `application.vnd.ms-excel` or `application.octet-stream`  
**Impact**: UI doesn't render content properly  
**Root Cause**: MIME detection not working correctly for CSV files  
**Evidence**: User screenshot shows wrong MIME types in Artifacts panel

### 4. 🔴 LLM Not Receiving Tool Outputs
**Symptom**: Tools succeed but LLM says "no results" or "dataset is empty"  
**Impact**: Complete failure of data analysis workflow  
**Root Cause**: Message formatting in guards not reaching LLM  
**Evidence**:
```
# Tools succeed
2025-10-22 20:17:48 - tools - INFO - [SUCCESS] analyze_dataset_tool (5.48s)
2025-10-22 20:17:50 - tools - INFO - [SUCCESS] describe_tool_guard (0.07s)

# But LLM says: "It seems that the analysis and description of the dataset have returned no results"
```

## Root Cause Analysis

### The Data Flow
```
1. User uploads CSV → 
2. analyze_dataset_tool executes (SUCCESS) →
3. head_tool_guard executes (SUCCESS) → 
4. describe_tool_guard executes (SUCCESS) →
5. ??? Message not reaching LLM ???
```

### Suspected Issues
1. **Guards format output but ADK doesn't pass it to LLM**
   - Guards set `result["message"]`, `result["ui_text"]`, `result["content"]`
   - But LLM receives empty response

2. **Tool wrapper strips formatted output**
   - `safe_tool_wrapper` in `agent.py` might be overriding guard output
   - Or artifact routing is replacing the message

3. **Logger misconfiguration**
   - Guards use `logging.getLogger(__name__)` 
   - But logs don't appear in `agent.log`
   - Suggests logger for `head_describe_guard` module not configured

## Fix Strategy

### Fix 1: Enable Guard Logging
- Check logger configuration in agent startup
- Ensure `head_describe_guard` logger writes to agent.log
- Set log level to INFO for all guard modules

### Fix 2: Stop Unstructured Tool Auto-Calls
- Check `routers.py` and `agent.py` for automatic unstructured tool triggers
- Add check: only call `list_unstructured_tool` if `ENABLE_UNSTRUCTURED=1`
- Or remove from auto-execution list for CSV uploads

### Fix 3: Fix MIME Detection
- Already fixed in `artifact_manager.py` and `artifacts_io.py`
- But CSV files still showing wrong MIME
- Need to check upload handler MIME detection

### Fix 4: Ensure Tool Output Reaches LLM
- Verify `safe_tool_wrapper` preserves `message`, `ui_text`, `content` fields
- Check if artifact routing is overwriting message
- Add explicit logging of final tool result before returning to ADK

## Priority
1. **CRITICAL**: Fix #4 (LLM not seeing outputs) - blocks all functionality
2. **HIGH**: Fix #2 (unstructured tool calls) - confuses LLM
3. **MEDIUM**: Fix #1 (logging) - needed for debugging
4. **LOW**: Fix #3 (MIME types) - already partially fixed

## Next Steps
1. Add extensive logging to trace where messages get lost
2. Check `safe_tool_wrapper` in `agent.py` for message handling
3. Check ADK integration point where tool results are returned
4. Test with simple case: call `head_tool_guard` directly and verify LLM sees output

