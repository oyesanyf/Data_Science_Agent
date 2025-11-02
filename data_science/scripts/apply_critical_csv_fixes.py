#!/usr/bin/env python3
"""
Apply _resolve_csv_path() to CRITICAL user-facing tools that are called first.

These tools are typically the first called after upload, so they MUST use the uploaded file.
"""

import re
from pathlib import Path

# Tools that users commonly call first after uploading data
CRITICAL_TOOLS = [
    'describe_tool',        # ✅ Already fixed
    'head_tool',            # ✅ Already fixed  
    'shape_tool',           # ✅ Already fixed
    'stats_tool',           # ✅ Already fixed
    'analyze_dataset_tool', # ✅ Already fixed
    'plot_tool',            # ✅ Already fixed
    'train_tool',           # ❌ NEEDS FIX
    'predict_tool',         # ❌ NEEDS FIX
    'classify_tool',        # ❌ NEEDS FIX
    'recommend_model_tool', # ❌ NEEDS FIX
    'auto_analyze_and_model_tool', # ❌ NEEDS FIX
    'split_data_tool',      # ❌ NEEDS FIX
    'select_features_tool', # ❌ NEEDS FIX
    'scale_data_tool',      # ❌ NEEDS FIX
    'encode_data_tool',     # ❌ NEEDS FIX
    'impute_simple_tool',   # ❌ NEEDS FIX
    'smart_cluster_tool',   # ❌ NEEDS FIX
    'train_classifier_tool', # ❌ NEEDS FIX
    'train_regressor_tool',  # ❌ NEEDS FIX
]

def add_resolver_to_tool(content: str, tool_name: str) -> str:
    """Add _resolve_csv_path to a specific tool."""
    
    # Find the tool definition
    pattern = rf'(def {tool_name}\([^)]*csv_path: str = ""[^)]*\) -> Dict\[str, Any\]:)\n((?:    """[^"]*"""\n)?)(    .*?tool_context = kwargs\.get\("tool_context"\)\n)'
    
    def replacer(match):
        func_def = match.group(1)
        docstring = match.group(2)
        context_line = match.group(3)
        
        # Check if _resolve_csv_path already exists in the next few lines
        end_pos = match.end()
        next_500_chars = content[end_pos:end_pos + 500]
        if '_resolve_csv_path' in next_500_chars:
            return match.group(0)  # Already fixed
        
        # Add resolver right after tool_context extraction
        resolver_line = f'    csv_path = _resolve_csv_path(csv_path, tool_context, "{tool_name.replace("_tool", "")}")\n'
        return f'{func_def}\n{docstring}{context_line}{resolver_line}'
    
    new_content = re.sub(pattern, replacer, content, count=1)
    
    if new_content != content:
        return new_content, True
    else:
        return content, False

def main():
    wrapper_file = Path(__file__).parent.parent / "adk_safe_wrappers.py"
    content = wrapper_file.read_text(encoding='utf-8')
    
    fixed_count = 0
    already_fixed_count = 0
    
    print("\n" + "="*70)
    print("APPLYING _resolve_csv_path TO CRITICAL TOOLS")
    print("="*70)
    
    for tool_name in CRITICAL_TOOLS:
        new_content, was_fixed = add_resolver_to_tool(content, tool_name)
        if was_fixed:
            content = new_content
            fixed_count += 1
            print(f"  ✅ {tool_name}")
        else:
            already_fixed_count += 1
            print(f"  ⏭️  {tool_name} (already fixed)")
    
    if fixed_count > 0:
        wrapper_file.write_text(content, encoding='utf-8')
        print("\n" + "="*70)
        print(f"✅ APPLIED FIX TO {fixed_count} TOOLS")
        print(f"⏭️  {already_fixed_count} TOOLS ALREADY CORRECT")
        print("="*70)
        print("\n🚀 ALL CRITICAL TOOLS NOW USE UPLOADED FILES!")
        return True
    else:
        print("\n" + "="*70)
        print(f"✅ ALL {already_fixed_count} CRITICAL TOOLS ALREADY CORRECT")
        print("="*70)
        return False

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

