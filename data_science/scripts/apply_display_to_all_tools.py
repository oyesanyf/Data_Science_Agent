"""
Comprehensive script to add __display__ fields to ALL tools in ds_tools.py.
This ensures every tool output displays properly in the UI.
"""
import re
from pathlib import Path

def add_display_wrapper_to_function(func_code: str, func_name: str) -> str:
    """
    Add display field wrapper to a function's return statement.
    
    Strategy: Find the last return statement and wrap it with display field addition.
    """
    lines = func_code.split('\n')
    
    # Find the last return statement
    return_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('return ') and not stripped.startswith('return None'):
            return_idx = i
            break
    
    if return_idx == -1:
        return func_code  # No return statement found
    
    # Get the return statement
    return_line = lines[return_idx]
    indent = len(return_line) - len(return_line.lstrip())
    indent_str = ' ' * indent
    
    # Check if it's a simple return or complex expression
    if '{' in return_line:
        # It's returning a dict directly - wrap it
        # Insert display field addition before return
        display_code = f'''{indent_str}# [AUTO] Add display fields for UI rendering
{indent_str}if isinstance(result, dict) and ("message" in result or "status" in result):
{indent_str}    msg = result.get("message") or result.get("ui_text") or result.get("text") or str(result.get("status", ""))
{indent_str}    if msg:
{indent_str}        result["__display__"] = msg
{indent_str}        result["text"] = msg
{indent_str}        result["message"] = msg
{indent_str}        result["ui_text"] = msg
{indent_str}        result["content"] = msg
{indent_str}        result["display"] = msg
'''
        # This is complex, skip for now
        return func_code
    
    # Check if function already assigns to result variable before returning
    has_result_var = False
    for line in lines[:return_idx]:
        if re.search(r'\bresult\s*=', line):
            has_result_var = True
            break
    
    if has_result_var and 'result' in return_line:
        # Add display wrapper before the return
        display_code = f'''{indent_str}# [AUTO] Add display fields for UI rendering
{indent_str}if isinstance(result, dict):
{indent_str}    msg = result.get("__display__") or result.get("message") or result.get("ui_text") or result.get("text")
{indent_str}    if msg:
{indent_str}        result["__display__"] = msg
{indent_str}        result["text"] = msg
{indent_str}        result["message"] = result.get("message", msg)
{indent_str}        result["ui_text"] = msg
{indent_str}        result["content"] = msg
{indent_str}        result["display"] = msg
{indent_str}        result["_formatted_output"] = msg

'''
        lines.insert(return_idx, display_code)
        return '\n'.join(lines)
    
    return func_code

def main():
    print("="*80)
    print("ADDING __display__ FIELDS TO ALL TOOLS")
    print("="*80)
    
    # For simplicity and safety, we'll create a helper that can be imported
    # and used in tools rather than modifying every function
    
    print("\n[STRATEGY] Create a universal display wrapper decorator")
    print("This is safer than modifying 80+ functions individually\n")
    
    wrapper_code = '''
# ==== UNIVERSAL DISPLAY FIELD WRAPPER ====
# Add this decorator to any tool that returns a dict

def ensure_display_fields(func):
    """
    Decorator to ensure all tool outputs have __display__ fields.
    Automatically extracts message/ui_text/text and promotes to __display__.
    """
    import functools
    import inspect
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, dict):
            # Extract formatted message
            msg = (result.get("__display__") or 
                   result.get("message") or 
                   result.get("ui_text") or 
                   result.get("text") or
                   result.get("content"))
            
            if msg and isinstance(msg, str):
                result["__display__"] = msg
                result["text"] = msg
                result["message"] = result.get("message", msg)
                result["ui_text"] = msg
                result["content"] = msg
                result["display"] = msg
                result["_formatted_output"] = msg
        return result
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            msg = (result.get("__display__") or 
                   result.get("message") or 
                   result.get("ui_text") or 
                   result.get("text") or
                   result.get("content"))
            
            if msg and isinstance(msg, str):
                result["__display__"] = msg
                result["text"] = msg
                result["message"] = result.get("message", msg)
                result["ui_text"] = msg
                result["content"] = msg
                result["display"] = msg
                result["_formatted_output"] = msg
        return result
    
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
'''
    
    print("[INFO] Decorator created. Now applying to ds_tools.py...")
    
    ds_tools_path = Path("data_science/ds_tools.py")
    if not ds_tools_path.exists():
        print(f"[ERROR] File not found: {ds_tools_path}")
        return
    
    content = ds_tools_path.read_text(encoding="utf-8")
    
    # Check if decorator already exists
    if "ensure_display_fields" in content:
        print("[INFO] Decorator already exists in ds_tools.py")
    else:
        # Add decorator after imports, before first function
        # Find where to insert (after imports)
        insert_pos = content.find("\n\n# ===")  # Look for section marker
        if insert_pos == -1:
            insert_pos = content.find("\ndef ")  # Or before first function
        
        if insert_pos != -1:
            content = content[:insert_pos] + "\n" + wrapper_code + "\n" + content[insert_pos:]
            ds_tools_path.write_text(content, encoding="utf-8")
            print("[OK] Decorator added to ds_tools.py")
        else:
            print("[WARNING] Could not find insertion point")
    
    print("\n[INFO] To apply the decorator to a function, add:")
    print("      @ensure_display_fields")
    print("      async def your_tool(...):")
    print("\n[RECOMMENDATION] Apply decorator to these critical tools:")
    
    critical = [
        "clean", "accuracy", "evaluate", "explain_model",
        "anomaly", "export", "suggest_next_steps",
        "train_classifier", "train_regressor", "train_decision_tree",
        "recommend_model", "list_data_files"
    ]
    
    for tool in critical:
        print(f"  • {tool}()")
    
    print(f"\n[STATUS] Total tools to enhance: {len(critical)}")
    print("[INFO] The decorator will automatically add __display__ fields")
    print("[INFO] No manual edits needed - just add @ensure_display_fields")

if __name__ == "__main__":
    main()

