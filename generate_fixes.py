"""Generate the exact search-replace patterns for all async tools"""
import re
from pathlib import Path

# Read the file
wrappers_path = Path("data_science/adk_safe_wrappers.py")
with open(wrappers_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Read ds_tools.py to find async functions
ds_tools_path = Path("data_science/ds_tools.py")
with open(ds_tools_path, 'r', encoding='utf-8') as f:
    ds_tools_content = f.read()

async_functions = set()
for match in re.finditer(r'^async def (\w+)\(', ds_tools_content, re.MULTILINE):
    async_functions.add(match.group(1))

# Find patterns like: result = func_name(...)\n    return _ensure_ui_display(result, ...)
pattern = r'    result = (\w+)\(([^)]+(?:\([^)]*\)[^)]*)*)\)\n    return _ensure_ui_display\(result,'

matches = list(re.finditer(pattern, content))

fixes_needed = []
for match in matches:
    func_name = match.group(1)
    if func_name in async_functions and '_run_async' not in match.group(0):
        fixes_needed.append({
            'func': func_name,
            'old': match.group(0),
            'params': match.group(2)
        })

print(f"Found {len(fixes_needed)} tools needing async fixes:\n")
for fix in fixes_needed[:10]:  # Show first 10
    print(f"- {fix['func']}")

if len(fixes_needed) > 10:
    print(f"... and {len(fixes_needed) - 10} more")

# Generate the fix patterns
print(f"\n\nGenerate these {len(fixes_needed)} fixes:")
for i, fix in enumerate(fixes_needed, 1):
    old_line = f"    result = {fix['func']}({fix['params']})"
    new_line = f"    # {fix['func']} is async, must use _run_async\n    result = _run_async({fix['func']}({fix['params']}))"
    print(f"{i}. {fix['func']}")

