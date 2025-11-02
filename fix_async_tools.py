"""
Automatically fix all tool wrappers that call async functions without _run_async().
"""
import re
from pathlib import Path

# Read ds_tools.py to find all async functions
ds_tools_path = Path("data_science/ds_tools.py")
with open(ds_tools_path, 'r', encoding='utf-8') as f:
    ds_tools_content = f.read()

# Find all async function names
async_functions = set()
for match in re.finditer(r'^async def (\w+)\(', ds_tools_content, re.MULTILINE):
    async_functions.add(match.group(1))

print(f"Found {len(async_functions)} async functions")

# Read adk_safe_wrappers.py
wrappers_path = Path("data_science/adk_safe_wrappers.py")
with open(wrappers_path, 'r', encoding='utf-8') as f:
    original_content = f.read()

modified_content = original_content
fixes_made = []

# Pattern to find tool wrappers
tool_pattern = r'(def (\w+)_tool\([^)]*\)[^:]*:)(.*?)(?=\ndef |\Z)'

for tool_match in re.finditer(tool_pattern, modified_content, re.DOTALL):
    full_match = tool_match.group(0)
    tool_signature = tool_match.group(1)
    tool_name = tool_match.group(2)
    tool_body = tool_match.group(3)
    
    # Check if this tool imports from ds_tools
    import_match = re.search(r'from \.ds_tools import (\w+)', tool_body)
    if not import_match:
        continue
    
    imported_func = import_match.group(1)
    
    # Is the imported function async?
    if imported_func not in async_functions:
        continue
    
    # Does it already use _run_async?
    if '_run_async(' in tool_body:
        continue
    
    # Find the return statement that calls the async function
    # Pattern 1: return _ensure_ui_display(async_func(...), "name")
    pattern1 = rf'(return _ensure_ui_display\()({imported_func}\([^)]*(?:\([^)]*\)[^)]*)*\))(, "[^"]*"\))'
    match1 = re.search(pattern1, tool_body)
    
    if match1:
        # Replace with _run_async wrapped version
        old_line = match1.group(0)
        new_line = f"{match1.group(1)}_run_async({match1.group(2)}){match1.group(3)}"
        
        old_full = tool_signature + tool_body
        new_full = old_full.replace(old_line, new_line)
        
        # Also add a comment explaining the fix
        comment = f"    # {imported_func} is async, must use _run_async\n    result = _run_async({match1.group(2)})\n    return _ensure_ui_display(result, \"{tool_name}\")"
        
        # Better approach: split the return statement
        better_new = old_full.replace(
            old_line,
            f"\n    # {imported_func} is async, must use _run_async\n    result = _run_async({match1.group(2)})\n    return _ensure_ui_display(result, \"{tool_name}\")"
        )
        
        modified_content = modified_content.replace(old_full, better_new)
        fixes_made.append(f"{tool_name}_tool")
        print(f"[FIX] {tool_name}_tool - wrapped {imported_func}() with _run_async()")
        continue
    
    # Pattern 2: Direct return without _ensure_ui_display
    pattern2 = rf'return ({imported_func}\([^)]*(?:\([^)]*\)[^)]*)*\))'
    match2 = re.search(pattern2, tool_body)
    
    if match2:
        old_line = match2.group(0)
        new_line = f"return _run_async({match2.group(1)})"
        
        old_full = tool_signature + tool_body
        new_full = old_full.replace(old_line, new_line)
        
        modified_content = modified_content.replace(old_full, new_full)
        fixes_made.append(f"{tool_name}_tool")
        print(f"[FIX] {tool_name}_tool - wrapped {imported_func}() with _run_async()")

print(f"\nTotal fixes made: {len(fixes_made)}")

# Write back
if fixes_made:
    with open(wrappers_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    print(f"\n[OK] Updated {wrappers_path}")
else:
    print("\n[INFO] No fixes needed")

