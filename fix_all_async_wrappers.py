"""
Comprehensively fix all async wrapper calls in adk_safe_wrappers.py
"""
import re
from pathlib import Path

# Read ds_tools.py to find async functions
ds_tools_path = Path("data_science/ds_tools.py")
with open(ds_tools_path, 'r', encoding='utf-8') as f:
    ds_tools_content = f.read()

async_functions = set()
for match in re.finditer(r'^async def (\w+)\(', ds_tools_content, re.MULTILINE):
    async_functions.add(match.group(1))

print(f"Found {len(async_functions)} async functions in ds_tools.py\n")

# Read adk_safe_wrappers.py
wrappers_path = Path("data_science/adk_safe_wrappers.py")
with open(wrappers_path, 'r', encoding='utf-8') as f:
    content = f.read()

original_content = content
fixes_made = []

# Pattern 1: return _ensure_ui_display(async_func(...), "name")
# Should become: result = _run_async(async_func(...))\n    return _ensure_ui_display(result, "name")
for func_name in async_functions:
    # Match the inline pattern
    pattern = rf'return _ensure_ui_display\({func_name}\(([^)]+(?:\([^)]*\))*[^)]*)\), "({func_name})"\)'
    
    for match in re.finditer(pattern, content):
        old_text = match.group(0)
        
        # Skip if already has _run_async
        if '_run_async' in old_text:
            continue
        
        params = match.group(1)
        tool_name = match.group(2)
        
        new_text = f'# {func_name} is async, must use _run_async\n    result = _run_async({func_name}({params}))\n    return _ensure_ui_display(result, "{tool_name}")'
        
        content = content.replace(old_text, new_text)
        fixes_made.append(func_name)
        print(f"[FIX] {func_name} - split inline call to use _run_async()")

# Save if changes were made
if fixes_made:
    with open(wrappers_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n[OK] Fixed {len(fixes_made)} async function calls")
    print(f"[OK] Updated {wrappers_path}")
else:
    print("\n[INFO] No additional fixes needed")

# Report what was fixed
print(f"\nFixed functions: {', '.join(sorted(set(fixes_made)))}")

