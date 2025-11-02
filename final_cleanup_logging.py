#!/usr/bin/env python3
"""
Final cleanup script to ensure exactly one _log_tool_result_diagnostics before each return _ensure_ui_display
"""
import re
from pathlib import Path

def final_cleanup(file_path):
    """Clean up all duplicates and ensure proper logging."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    skip_next = False
    modified = 0
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        
        # If this is a logging line, check if it's followed by return or another logging line
        if '_log_tool_result_diagnostics' in line:
            # Look ahead to see what's next (skip empty lines)
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            
            if j < len(lines):
                next_non_empty = lines[j]
                # If next line is return _ensure_ui_display, this logging is good
                if 'return _ensure_ui_display' in next_non_empty:
                    new_lines.append(line)
                # If next line is also logging, skip this one (keep the later one)
                elif '_log_tool_result_diagnostics' in next_non_empty:
                    modified += 1
                    continue  # Skip this logging line
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        # If this is a return _ensure_ui_display, check if logging exists before it
        elif 'return _ensure_ui_display' in line:
            # Look back to see if logging exists
            found_logging = False
            k = len(new_lines) - 1
            while k >= 0 and new_lines[k].strip() == '':
                k -= 1
            
            if k >= 0 and '_log_tool_result_diagnostics' in new_lines[k]:
                found_logging = True
            
            if not found_logging:
                # Need to add logging
                match = re.search(r'return _ensure_ui_display\((.+),\s*"([^"]+)"\)', line)
                if match:
                    expr = match.group(1).strip()
                    tool_name = match.group(2)
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    
                    if expr != 'result':
                        # Inline, need to extract
                        new_lines.append(f"{indent}result = {expr}\n")
                        new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")\n")
                        new_lines.append(f"{indent}return _ensure_ui_display(result, \"{tool_name}\")\n")
                        modified += 1
                        continue
                    else:
                        # Add logging before return
                        new_lines.append(f"{indent}_log_tool_result_diagnostics(result, \"{tool_name}\", \"raw_tool_output\")\n")
                        modified += 1
            
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"[OK] Fixed {modified} issues")
    return modified

if __name__ == "__main__":
    file_path = Path(__file__).parent / "data_science" / "adk_safe_wrappers.py"
    count = final_cleanup(file_path)
    print(f"[DONE] Total fixes: {count}")

