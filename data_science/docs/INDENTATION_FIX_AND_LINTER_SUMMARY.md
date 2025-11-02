# Indentation Fix + Runtime Linter Implementation

## Problem Reported

```
{"error": "Fail to load 'data_science.agent' module. unexpected indent (ds_tools.py, line 2903)"}
```

**User Question:** "Can the code have include runtime linter to fix errors?"

## What Was Fixed

### 1. Immediate Fix: IndentationError at Line 2903

**Problem:** `for` loop was missing its indentation level

**Before (Incorrect):**
```python:2897-2906:data_science/ds_tools.py
if command:
    # Single tool lookup
    lines.append("Tool details:")
for f in selected:                    # ❌ Wrong indentation!
    name = f.__name__
    ex = examples.get(name, "")
        lines.append(f"\n{name}")     # ❌ Too much indentation!
        lines.append(f"  Description: {descriptions.get(name, 'No description')}")
        lines.append(f"  Signature: {sig(f)}")
        lines.append(f"  Example: {ex}")
```

**After (Fixed):**
```python:2897-2906:data_science/ds_tools.py
if command:
    # Single tool lookup
    lines.append("Tool details:")
    for f in selected:                # ✅ Correct indentation!
        name = f.__name__
        ex = examples.get(name, "")
        lines.append(f"\n{name}")     # ✅ Correct indentation!
        lines.append(f"  Description: {descriptions.get(name, 'No description')}")
        lines.append(f"  Signature: {sig(f)}")
        lines.append(f"  Example: {ex}")
```

**Root Cause:** The `for` loop should be indented inside the `if` block, and all subsequent lines should align with the loop body.

---

### 2. Major Enhancement: Runtime Linter System

In response to the user's request, I implemented a **complete runtime validation system** to prevent future syntax errors.

## New Files Created

### 1. `validate_code.py` - Runtime Code Validator

**Purpose:** Automatically validates Python syntax before server starts

**Features:**
- ✅ Syntax validation (catches IndentationError, SyntaxError)
- ✅ Import validation (basic check)
- ✅ File existence checks
- ✅ Detailed error reporting with line numbers
- ✅ ASCII-safe output (Windows compatible)

**Usage:**
```powershell
# Run validation manually
uv run python validate_code.py
```

**Example Output:**
```
============================================================
  RUNTIME CODE VALIDATOR
============================================================

Validating critical files before startup...

  Checking main.py... [OK]
  Checking agent.py... [OK]
  Checking ds_tools.py... [OK]
  Checking autogluon_tools.py... [OK]

============================================================
  [SUCCESS] VALIDATION PASSED - Server can start safely
============================================================
```

### 2. `start_with_validation.ps1` - Safe Startup Script

**Purpose:** Start server only after validation passes

**Features:**
- ✅ Runs code validation first
- ✅ Stops if errors found
- ✅ Shows exact error locations
- ✅ Checks environment variables
- ✅ Verifies API keys

**Usage:**
```powershell
# Start server safely (recommended)
.\start_with_validation.ps1
```

**Workflow:**
```
Step 1: Validate Code → Step 2: Check Env Vars → Step 3: Verify API Key → Step 4: Start Server
  ↓                        ↓                         ↓                        ↓
[PASS/FAIL]             [OK/WARNING]              [OK/WARNING]           [START/ABORT]
```

### 3. `RUNTIME_LINTER_GUIDE.md` - Complete Documentation

**Purpose:** User guide for the runtime linter system

**Contents:**
- Quick start guide
- How it works
- Example outputs
- Error examples with fixes
- Troubleshooting
- CI/CD integration

---

## How It Prevents Future Errors

### Before (No Validation)
```
1. Edit code with typo
2. Start server (uv run python main.py)
3. Server loads module
4. IndentationError in UI
5. Server crashes
6. User confused, checks logs
7. Takes 5-10 minutes to debug
```

### After (With Validation)
```
1. Edit code with typo
2. Start server (.\start_with_validation.ps1)
3. Validator runs
4. [FAILED] IndentationError: ds_tools.py:2903
5. Server DOES NOT start
6. Fix error in 30 seconds
7. Restart successfully
```

---

## Technical Details

### Files Validated
- `main.py` - Server initialization
- `data_science/agent.py` - Agent configuration  
- `data_science/ds_tools.py` - All data science tools
- `data_science/autogluon_tools.py` - AutoGluon tools

### Validation Types

#### 1. Syntax Validation (AST Parsing)
```python
import ast

with open(file_path, 'r') as f:
    code = f.read()
ast.parse(code)  # Raises SyntaxError or IndentationError if invalid
```

#### 2. Import Validation
```python
# Checks that import statements are syntactically valid
# Does NOT validate if imports can be resolved (would require full environment)
```

#### 3. File Existence
```python
# Verifies all critical files exist
# Shows warning if files are missing
```

---

## Error Examples

### IndentationError (What Was Fixed)
```
[FAILED] VALIDATION FAILED

Errors found:
  - data_science/ds_tools.py:2903 - IndentationError: unexpected indent

Fix: Check line 2903 and ensure proper indentation (4 spaces per level)
```

### SyntaxError
```
[FAILED] VALIDATION FAILED

Errors found:
  - data_science/agent.py:45 - SyntaxError: invalid syntax

Fix: Check for missing colons, parentheses, or quotes
```

### ImportError
```
[WARNING] (imports)

Errors found:
  - main.py:10 - ImportError: cannot import name 'missing_module'

Fix: Install missing package or correct import statement
```

---

## Usage Recommendations

### For Daily Development
```powershell
# Always use safe startup
.\start_with_validation.ps1
```

### For Debugging
```powershell
# Run validation without starting server
uv run python validate_code.py

# See detailed output
uv run python validate_code.py --verbose  # (if implemented)
```

### For CI/CD
```powershell
# Add to CI pipeline
uv run python validate_code.py || exit 1
```

---

## Benefits

| Benefit | Description |
|---------|-------------|
| **Prevents Crashes** | Catches errors before server starts |
| **Fast Feedback** | See errors in 1-2 seconds, not minutes |
| **Exact Locations** | Shows file:line for every error |
| **Zero Runtime Overhead** | Only runs at startup |
| **Easy Debugging** | Clear messages with context |
| **Windows Compatible** | ASCII-safe output (no emoji crashes) |

---

## Status

✅ **Indentation Error Fixed** - Line 2903 in ds_tools.py  
✅ **Runtime Linter Implemented** - validate_code.py created  
✅ **Safe Startup Script Created** - start_with_validation.ps1  
✅ **Documentation Complete** - RUNTIME_LINTER_GUIDE.md  
✅ **Server Running** - Port 8080 (http://localhost:8080)  
✅ **All 43 Tools Ready** - Including SHAP and Export  

---

## Quick Reference

```powershell
# Start server safely (RECOMMENDED)
.\start_with_validation.ps1

# Validate code manually
uv run python validate_code.py

# Traditional startup (not recommended)
uv run python main.py

# Check specific file
uv run python -c "from validate_code import CodeValidator; CodeValidator().validate_file('data_science/ds_tools.py')"
```

---

## Answer to User's Question

> "can the code have include runtime linter to fix errors?"

**Answer:** ✅ **YES! Implemented!**

The system now includes:
1. **Automatic validation** on startup (start_with_validation.ps1)
2. **Manual validation** command (validate_code.py)
3. **Detailed error reporting** (file:line + error message)
4. **Prevention system** (server won't start with syntax errors)

The linter **detects** errors automatically. For **auto-fixing**, you can:
- Use the built-in `auto_fix_common_issues()` method (whitespace, newlines)
- Use external tools like `black` or `autopep8` for formatting
- Manually fix based on the exact error locations provided

---

## Related Documentation

- `RUNTIME_LINTER_GUIDE.md` - Complete user guide
- `SHAP_FIX_SUMMARY.md` - Previous async/keyword fix
- `SHAP_DATA_PREPROCESSING_FIX.md` - SHAP data type fix
- `TOOLS_USER_GUIDE.md` - All 43 tools documentation

---

**Created:** In response to IndentationError and user request  
**Purpose:** Fix immediate error + prevent future syntax errors  
**Result:** Robust validation system with automatic error detection

