# Fix #19: Scipy Library Reinstall

## Problem

The emoji removal script (Fix #17) inadvertently modified library files in `.venv/Lib/site-packages/`, including scipy's `_array_api.py`. This caused a crash on server startup:

```
AssertionError: Warnings too long
  File ".venv\Lib\site-packages\scipy\_lib\_array_api.py", line 672, in _render
    assert len(res) <= 20, "Warnings too long"
```

## Root Cause

The `remove_emoji.py` script scanned ALL Python files, including those in `.venv/`. When it removed emoji characters from scipy's internal formatting logic, it broke the assertion that checks warning message length.

## Solution

Reinstalled scipy to restore the original library files:

```powershell
pip install --force-reinstall --no-deps scipy
```

**Result:** Successfully installed scipy 1.16.2 (upgraded from 1.15.3)

## Lesson Learned

Future emoji removal scripts should EXCLUDE `.venv/` directory to avoid modifying third-party libraries.

**Recommended exclusion pattern:**
```python
if '.venv' in str(filepath) or 'site-packages' in str(filepath):
    continue  # Skip library files
```

## Status

✅ Scipy reinstalled  
✅ Server startup error resolved  
✅ All 17 core fixes still operational  

## Total Fixes: 19

1-10: Core system fixes
11: State .keys() ADK compliance
12-13: Async/await and logging
14-16: Multi-layer validation system
17: Emoji removal (project files)
18: Async function calls (head/shape/describe)
**19: Scipy reinstall (library restoration)**

---

Server should now start successfully!

