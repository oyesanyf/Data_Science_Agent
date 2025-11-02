#!/usr/bin/env python3
"""
Script to add diagnostic logging to all tool functions in adk_safe_wrappers.py
"""
import re
from pathlib import Path

def add_logging_to_tools(file_path):
    """Add _log_tool_result_diagnostics before all return _ensure_ui_display statements."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    lines = content.split('\n')
    new_lines = []
    modified_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a return _ensure_ui_display line
        if '    return _ensure_ui_display(' in line:
            # Extract tool name from the return statement
            match = re.search(r'return _ensure_ui_display\([^,]+,\s*"([^"]+)"\)', line)
            if match:
                tool_name = match.group(1)
                
                # Check if logging already exists on previous line
                if i > 0 and '_log_tool_result_diagnostics' in lines[i-1]:
                    # Logging already exists, skip
                    new_lines.append(line)
                else:
                    # Need to add logging
                    # Check if the return statement has inline result calculation
                    if '_run_async(' in line or any(func in line for func in ['extract_text(', 'chunk_text(', 'semantic_search(', 'classify_text(', 'get_workspace_info(']):
                        # Extract the expression being passed to _ensure_ui_display
                        match_expr = re.search(r'return _ensure_ui_display\((.+),\s*"[^"]+"\)', line)
                        if match_expr:
                            expr = match_expr.group(1).strip()
                            indent = ' ' * (len(line) - len(line.lstrip()))
                            
                            # Add result assignment, logging, then return
                            new_lines.append(f"{indent}result = {expr}")
                            new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")")
                            new_lines.append(f"{indent}return _ensure_ui_display(result, \"{tool_name}\")")
                            modified_count += 1
                            i += 1
                            continue
                    else:
                        # Result is already assigned, just add logging before return
                        indent = ' ' * (len(line) - len(line.lstrip()))
                        new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")")
                        new_lines.append(line)
                        modified_count += 1
                        i += 1
                        continue
        
        new_lines.append(line)
        i += 1
    
    new_content = '\n'.join(new_lines)
    
    # Only write if changes were made
    if new_content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[OK] Modified {modified_count} tool functions")
        return modified_count
    else:
        print("[INFO] No changes needed")
        return 0

if __name__ == "__main__":
    file_path = Path(__file__).parent / "data_science" / "adk_safe_wrappers.py"
    count = add_logging_to_tools(file_path)
    print(f"Added diagnostic logging to {count} tools")

