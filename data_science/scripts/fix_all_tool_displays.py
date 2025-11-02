"""
Fix all ADK tool wrappers to use _ensure_ui_display for proper UI output.

This script automatically updates all tool wrappers in adk_safe_wrappers.py
to ensure they return properly formatted results for UI display.
"""

import re
from pathlib import Path

def fix_tool_displays():
    """Add _ensure_ui_display to all tool wrappers that don't have it."""
    
    file_path = Path(__file__).parent.parent / "adk_safe_wrappers.py"
    
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match tool functions and their return statements
    # Match: def xxx_tool(...) -> Dict[str, Any]:
    tool_pattern = re.compile(
        r'(def (\w+_tool)\([^)]*\) -> Dict\[str, Any\]:.*?)'  # Function signature
        r'(return\s+(.+?)(?=\n\ndef|\n\n#|$))',  # Return statement
        re.DOTALL
    )
    
    fixes_applied = 0
    already_fixed = 0
    
    def replace_return(match):
        nonlocal fixes_applied, already_fixed
        
        full_match = match.group(0)
        func_name = match.group(2)
        return_statement = match.group(3)
        return_value = match.group(4).strip()
        
        # Skip if already uses _ensure_ui_display
        if '_ensure_ui_display' in return_statement:
            already_fixed += 1
            return full_match
        
        # Extract the tool name (remove _tool suffix)
        tool_name = func_name.replace('_tool', '')
        
        # Build the new return statement
        new_return = f"return _ensure_ui_display({return_value}, \"{tool_name}\")"
        
        # Replace the return statement
        new_full = full_match.replace(return_statement, new_return)
        
        fixes_applied += 1
        print(f"  [OK] Fixed {func_name}")
        
        return new_full
    
    print("\nApplying fixes...")
    new_content = tool_pattern.sub(replace_return, content)
    
    print(f"\nWriting changes back to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] COMPLETE!")
    print(f"{'='*60}")
    print(f"Fixes applied: {fixes_applied}")
    print(f"Already fixed: {already_fixed}")
    print(f"Total tools: {fixes_applied + already_fixed}")
    print(f"\nAll tools now use _ensure_ui_display for proper UI output!")
    
    return fixes_applied

if __name__ == "__main__":
    print("="*60)
    print("FIX ALL TOOL DISPLAYS FOR UI OUTPUT")
    print("="*60)
    print()
    
    fixes = fix_tool_displays()
    
    if fixes > 0:
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Review the changes in adk_safe_wrappers.py")
        print("2. Restart the server")
        print("3. Test tool outputs in UI")
        print("\nAll tools will now display properly formatted output!")

