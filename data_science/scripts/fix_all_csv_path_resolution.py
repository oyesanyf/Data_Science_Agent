#!/usr/bin/env python3
"""
Apply _resolve_csv_path() to ALL tools that accept csv_path parameter.

This ensures EVERY tool uses the uploaded file from session state.
"""

import re
from pathlib import Path

def fix_csv_path_resolution():
    """Add csv_path = _resolve_csv_path(csv_path, tool_context, 'tool_name') to all tools."""
    
    wrapper_file = Path(__file__).parent.parent / "adk_safe_wrappers.py"
    content = wrapper_file.read_text(encoding='utf-8')
    
    # Pattern to find tool definitions with csv_path parameter
    # Matches: def tool_name_tool(...csv_path: str = "", **kwargs) -> Dict[str, Any]:
    tool_pattern = re.compile(
        r'(def (\w+)_tool\([^)]*csv_path: str = ""[^)]*\) -> Dict\[str, Any\]:)\n'
        r'((?:    """[^"]*"""\n)?)'  # Optional docstring
        r'(    .*?\n)'  # First line after def/docstring
    )
    
    fixes_applied = 0
    already_fixed = 0
    
    def add_resolver(match):
        nonlocal fixes_applied, already_fixed
        
        func_def = match.group(1)  # def tool_name_tool(...)
        tool_name = match.group(2)  # tool_name (without _tool suffix)
        docstring = match.group(3)  # Optional docstring
        first_line = match.group(4)  # First line after def
        
        # Check if this tool already has _resolve_csv_path
        # We need to look ahead to see the full function body
        func_start = match.start()
        func_body_preview = content[func_start:func_start + 1000]
        
        if '_resolve_csv_path' in func_body_preview:
            already_fixed += 1
            return match.group(0)  # Return unchanged
        
        # Check if tool_context is extracted on the first line
        if 'tool_context = kwargs.get("tool_context")' in first_line:
            # Add resolver right after tool_context extraction
            resolver_line = f'    csv_path = _resolve_csv_path(csv_path, tool_context, "{tool_name}")\n'
            result = f'{func_def}\n{docstring}{first_line}{resolver_line}'
            fixes_applied += 1
            return result
        else:
            # Need to add tool_context extraction first, then resolver
            resolver_lines = (
                f'    tool_context = kwargs.get("tool_context")\n'
                f'    csv_path = _resolve_csv_path(csv_path, tool_context, "{tool_name}")\n'
            )
            result = f'{func_def}\n{docstring}{resolver_lines}{first_line}'
            fixes_applied += 1
            return result
    
    # Apply fixes
    new_content = tool_pattern.sub(add_resolver, content)
    
    if fixes_applied > 0:
        wrapper_file.write_text(new_content, encoding='utf-8')
        print(f"[OK] Applied _resolve_csv_path() to {fixes_applied} tools")
        print(f"[OK] {already_fixed} tools already had the fix")
        print(f"[OK] Total tools with csv_path: {fixes_applied + already_fixed}")
        return True
    else:
        print(f"[OK] All {already_fixed} tools already have _resolve_csv_path()")
        return False

if __name__ == "__main__":
    try:
        if fix_csv_path_resolution():
            print("\n✅ ALL TOOLS NOW USE UPLOADED FILES FROM STATE!")
        else:
            print("\n✅ No changes needed - all tools already correct!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

