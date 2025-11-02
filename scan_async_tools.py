"""
Scan for tool wrappers that might not be handling async functions correctly.
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

print(f"Found {len(async_functions)} async functions in ds_tools.py")
print()

# Read adk_safe_wrappers.py to check tool wrappers
wrappers_path = Path("data_science/adk_safe_wrappers.py")
with open(wrappers_path, 'r', encoding='utf-8') as f:
    wrappers_content = f.read()

# Find all tool wrappers
tool_pattern = r'def (\w+)_tool\([^)]*\)[^:]*:.*?(?=\ndef |$)'
tools = list(re.finditer(tool_pattern, wrappers_content, re.DOTALL))

print(f"Found {len(tools)} tool wrappers in adk_safe_wrappers.py")
print()

# Check each tool wrapper
issues = []
for tool_match in tools:
    tool_name = tool_match.group(1)
    tool_body = tool_match.group(0)
    
    # Check if this tool imports from ds_tools
    import_match = re.search(r'from \.ds_tools import (\w+)', tool_body)
    if not import_match:
        continue
    
    imported_func = import_match.group(1)
    
    # Is the imported function async?
    if imported_func in async_functions:
        # Does the wrapper use _run_async?
        if '_run_async(' not in tool_body:
            issues.append({
                'tool': f"{tool_name}_tool",
                'async_func': imported_func,
                'line': tool_body[:100]
            })

print(f"Found {len(issues)} tools that might not handle async correctly:")
print()
for issue in issues[:20]:  # Show first 20
    print(f"[X] {issue['tool']} calls async {issue['async_func']} without _run_async()")

if len(issues) > 20:
    print(f"... and {len(issues) - 20} more")

