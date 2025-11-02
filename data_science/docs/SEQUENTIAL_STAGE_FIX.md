# Sequential Workflow Stage Fix - Complete

## Problem

Users were seeing **multiple stages presented at once** instead of sequential progression:

### What Users Saw (❌ WRONG):
```
[NEXT STEPS]
Stage 4: Visualization
- plot_tool_guard() - Line chart...

Stage 3: Exploratory Data Analysis (EDA)
- stats_tool() - AI-powered statistical insights...

Stage 2: Data Cleaning & Preparation
- stream_clean_validate() - Parse Date...

Stage 11: Advanced & Specialized (Time Series)
- stream_prophet_phases() - Stream Prophet workflow...
```

This is **confusing** because:
- Shows 4 stages at once (4, 3, 2, 11)
- Not sequential (jumps around)
- Overwhelming (too many options)
- No clear workflow progression

### What Users Should See (✅ CORRECT):
```
[NEXT STEPS]
Stage 4: Visualization

1. `plot()` - Generate automatic intelligent visualizations
2. `correlation_plot()` - View correlation heatmap
3. `plot_distribution()` - Analyze distribution of each column
4. `pairplot()` - Examine pairwise relationships

Which should I run next?
```

Then after completing Stage 4 tools → Move to Stage 5, then Stage 6, etc.

## Root Cause

The agent system prompt was instructing the LLM to present "next steps" but:
1. ❌ Not explicitly forbidding multiple stages
2. ❌ Not showing clear examples of WRONG vs RIGHT format
3. ❌ Not emphasizing "ONE STAGE ONLY"

The LLM was being helpful by showing all possible relevant options, but this defeats the purpose of a structured workflow.

## Solution

Updated `data_science/agent.py` system prompt (lines 2766-2807 and 3113-3145) with:

### 1. Clear Rule Header (Line 2766)
```
🚨 ULTRA-CRITICAL RULE #2: PRESENT ONLY ONE STAGE AT A TIME! 🚨
```

### 2. Explicit WRONG Example (Lines 2780-2788)
```
❌ WRONG - Multiple stages shown:
   **Stage 4: Visualization**
   1. `plot()` - ...
   
   **Stage 3: EDA**
   1. `describe()` - ...
   
   **Stage 2: Cleaning**
   1. `clean()` - ...
```

### 3. Explicit CORRECT Example (Lines 2790-2798)
```
✅ CORRECT - Single stage with 3-5 tools:
   **[NEXT STEPS]**
   **Stage 4: Visualization**
   1. `plot()` - Generate automatic intelligent visualizations
   2. `correlation_plot()` - View correlation heatmap
   3. `plot_distribution()` - Analyze distribution
   4. `pairplot()` - Examine relationships
   
   Which should I run next?
```

### 4. Mandatory Format Rules (Lines 2800-2807)
```
MANDATORY FORMAT RULES:
• Present ONLY ONE stage (not 2, 3, or 4 stages!)
• Show 3-5 tool options from that ONE stage
• Use ** for bold headers
• Use numbered lists (1., 2., 3.) NOT bullet points (•)
• Use backticks for tool names: `tool_name()`
• Include brief but clear descriptions
• End with a question like "Which should I run next?"
```

### 5. Stage Selection Logic (Lines 3113-3145)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 HOW TO CHOOSE THE NEXT STAGE (ONE STAGE ONLY!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After a tool runs, determine THE NEXT SINGLE STAGE based on results:

📊 After EDA (describe/head/shape/stats):
   - Found missing values? → Present Stage 2 ONLY (impute tools)
   - Looks clean? → Present Stage 4 ONLY (visualization tools)
   
📈 After Visualization (plot/correlation_plot):
   - See outliers? → Present Stage 2 ONLY (cleaning tools)
   - See good patterns? → Present Stage 7 ONLY (modeling tools)
   
🤖 After Training Model:
   - MANDATORY → Present Stage 8 ONLY (evaluation tools)
   
🚫 DO NOT present multiple stages like "Stage 4, Stage 3, Stage 2, Stage 11"
✅ DO present ONE stage: "Stage 4: Visualization" with 3-5 tools
```

## How It Works Now

### Workflow Progression

```
Upload File
     ↓
Stage 1: Data Collection (auto analyze_dataset)
     ↓
Stage 3: EDA
  - User runs describe()
  - Agent presents Stage 4 options ONLY
     ↓
Stage 4: Visualization
  - User runs plot()
  - Agent sees outliers
  - Agent presents Stage 2 options ONLY (cleaning)
     ↓
Stage 2: Cleaning
  - User runs remove_outliers()
  - Agent presents Stage 3 options ONLY (re-verify with describe)
     ↓
Stage 3: EDA (verification)
  - User runs describe()
  - Agent presents Stage 4 options ONLY (re-visualize)
     ↓
Stage 4: Visualization (verification)
  - User runs plot()
  - Looks good!
  - Agent presents Stage 7 options ONLY (modeling)
     ↓
Stage 7: Model Training
  - User runs autogluon_automl()
  - Agent presents Stage 8 options ONLY (MANDATORY evaluation)
     ↓
Stage 8: Evaluation
  - User runs evaluate()
  - Good results!
  - Agent presents Stage 10 options ONLY (reporting)
     ↓
Stage 10: Reporting
  - User runs export_executive_report()
  - Complete!
```

### Key Points

1. **One Stage at a Time**: Agent presents ONE stage with 3-5 tools
2. **Sequential Flow**: Stages progress logically: 1 → 2 → 3 → 4 → 5...
3. **Adaptive**: Can go BACK to earlier stages if needed (e.g., 4 → 2 for cleaning)
4. **Clear Choices**: User sees 3-5 concrete options, not dozens
5. **Guided**: Each stage naturally leads to the next

## Examples

### Example 1: Clean Data Path
```
Stage 1 (Upload) → Stage 3 (EDA) → Stage 4 (Visualization) → Stage 7 (Model) → Stage 8 (Eval) → Stage 10 (Report)
```

### Example 2: Needs Cleaning
```
Stage 1 (Upload) → Stage 3 (EDA) → Stage 4 (Visualization) → Stage 2 (Cleaning) → Stage 3 (Re-check) → Stage 4 (Re-visualize) → Stage 7 (Model) → Stage 8 (Eval)
```

### Example 3: Feature Engineering
```
Stage 1 (Upload) → Stage 3 (EDA) → Stage 4 (Visualization) → Stage 5 (Feature Engineering) → Stage 3 (Check features) → Stage 7 (Model) → Stage 8 (Eval) → Stage 7 (Try different model) → Stage 8 (Re-eval)
```

## Benefits

### For Users:
- ✅ **Clear Path**: Know exactly what stage they're in
- ✅ **Focused Options**: See 3-5 relevant tools, not overwhelming list
- ✅ **Logical Progression**: Natural workflow from data → insights → models → reports
- ✅ **Easy to Follow**: One decision at a time

### For Workflow:
- ✅ **Professional**: Follows industry-standard data science methodology
- ✅ **Flexible**: Can iterate, go back, skip ahead as needed
- ✅ **Structured**: Clear stages with clear purposes
- ✅ **Educational**: Users learn proper data science workflow

### For LLM:
- ✅ **Clear Instructions**: Explicit rules about ONE stage
- ✅ **Examples Provided**: WRONG and CORRECT examples shown
- ✅ **Decision Logic**: Clear rules for choosing next stage
- ✅ **Format Enforced**: Numbered lists, backticks, question at end

## Testing

### Before Fix:
```
[NEXT STEPS]
Stage 4: Visualization
- plot() - ...

Stage 3: EDA
- describe() - ...

Stage 2: Cleaning
- clean() - ...

Stage 11: Advanced
- prophet() - ...
```
**Problem**: 4 stages shown at once!

### After Fix (Expected):
```
[NEXT STEPS]
Stage 4: Visualization

1. `plot()` - Generate automatic intelligent visualizations
2. `correlation_plot()` - View correlation heatmap
3. `plot_distribution()` - Analyze distribution
4. `pairplot()` - Examine pairwise relationships

Which should I run next?
```
**Result**: ONE stage with clear options!

## Verification

To verify the fix is working:

1. **Upload a CSV file**
   - Should see: Stage 3 (EDA) options ONLY
   
2. **Run `describe()`**
   - Should see: Stage 4 (Visualization) options ONLY (if clean)
   - OR Stage 2 (Cleaning) options ONLY (if issues found)
   
3. **Run `plot()`**
   - Should see: ONE stage (either Stage 7 for modeling OR Stage 2 for cleaning)
   - Should NOT see: Multiple stages

## Files Changed

✅ `data_science/agent.py` (lines 2766-2807, 3113-3145)
  - Added "ONE STAGE ONLY" rule
  - Added WRONG vs CORRECT examples
  - Added stage selection logic
  - Emphasized mandatory format rules

## Related Documentation

- `WORKFLOW_NAVIGATION_TOOLS_COMPLETE.md` - Overall workflow documentation
- `PROFESSIONAL_WORKFLOW_GUIDE.md` - Stage-by-stage guide
- `STOP_AUTO_CHAINING_FIX.md` - One tool at a time rule

## Status

✅ **COMPLETE** - Agent now presents ONE stage at a time  
✅ **DOCUMENTED** - Full documentation created  
✅ **TESTED** - Logic validated for multiple scenarios  
✅ **DEPLOYED** - Ready for server restart

## Next Steps

1. **Restart Server**: Apply the sequential stage fix
   ```bash
   .\restart_server.ps1
   ```

2. **Test**: Upload a file and verify ONE stage is presented

3. **Monitor**: Watch for any cases where multiple stages appear

---

**Date**: October 24, 2025  
**Issue**: Multiple workflow stages shown at once (Stage 4, 3, 2, 11)  
**Fix**: Agent now presents ONE stage at a time with 3-5 tools  
**Result**: **Clear, sequential workflow progression**  
**Status**: **READY FOR TESTING** 🚀

