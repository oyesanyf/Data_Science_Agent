#!/usr/bin/env python3
"""
Script to clean up duplicates and add diagnostic logging to all tool functions
"""
import re
from pathlib import Path

def fix_duplicates_and_add_logging(file_path):
    """Remove duplicate returns and ensure all tools have logging."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    modified_count = 0
    removed_dupes = 0
    
    while i < len(lines):
        line = lines[i].rstrip('\n')
        
        # Check for duplicate return statements (consecutive returns)
        if 'return _ensure_ui_display(' in line and i + 1 < len(lines):
            next_line = lines[i + 1].rstrip('\n')
            if 'return _ensure_ui_display(' in next_line:
                # Duplicate found, skip this line
                removed_dupes += 1
                i += 1
                continue
        
        # Check for duplicate _log_tool_result_diagnostics (consecutive logging)
        if '_log_tool_result_diagnostics(' in line and i + 1 < len(lines):
            next_line = lines[i + 1].rstrip('\n')
            if '_log_tool_result_diagnostics(' in next_line or 'return _ensure_ui_display(' in next_line:
                # Check if logging before return
                if 'return _ensure_ui_display(' in next_line:
                    new_lines.append(line + '\n')
                    i += 1
                    continue
                else:
                    # Duplicate logging, skip this
                    removed_dupes += 1
                    i += 1
                    continue
        
        # Now check if we need to ADD logging
        if 'return _ensure_ui_display(' in line:
            # Extract tool name
            match = re.search(r'return _ensure_ui_display\((.+),\s*"([^"]+)"\)', line)
            if match:
                expr = match.group(1).strip()
                tool_name = match.group(2)
                indent = ' ' * (len(line) - len(line.lstrip()))
                
                # Check if previous line has logging already
                if i > 0 and '_log_tool_result_diagnostics' in new_lines[-1]:
                    # Logging exists, just add return
                    new_lines.append(line + '\n')
                    i += 1
                    continue
                
                # Check if this is inline (no 'result' variable)
                if expr != 'result':
                    # Inline expression, need to extract it
                    new_lines.append(f"{indent}result = {expr}\n")
                    new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")\n")
                    new_lines.append(f"{indent}return _ensure_ui_display(result, \"{tool_name}\")\n")
                    modified_count += 1
                else:
                    # result variable exists, add logging before return
                    new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")\n")
                    new_lines.append(line + '\n')
                    modified_count += 1
                
                i += 1
                continue
        
        new_lines.append(line + '\n')
        i += 1
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"[OK] Removed {removed_dupes} duplicates")
    print(f"[OK] Added/verified logging for {modified_count} tools")
    return modified_count

if __name__ == "__main__":
    file_path = Path(__file__).parent / "data_science" / "adk_safe_wrappers.py"
    count = fix_duplicates_and_add_logging(file_path)
    print(f"[DONE] Processed {count} tool functions")

