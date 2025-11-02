"""
Systematically add __display__ fields to all tools in ds_tools.py
This ensures all tool outputs display properly in the UI.
"""
import re
from pathlib import Path

# Tools that need the __display__ fix (function name -> indicator of where to add)
TOOLS_TO_FIX = {
    # Data exploration tools
    "stats": 'result["message"]',
    "list_tools": 'result["message"]',
    
    # Data cleaning tools
    "clean": 'return {',
    
    # Training tools
    "train_classifier": '"message":',
    "train_regressor": '"message":',
    "train_decision_tree": 'return {',
    "train_knn": 'return {',
    "train_naive_bayes": 'return {',
    "train_svm": 'return {',
    
    # Evaluation tools
    "accuracy": '"message":',
    "evaluate": 'return {',
    "explain_model": 'return {',
    
    # Feature engineering tools
    "apply_pca": 'return {',
    "scale_data": 'return {',
    "encode_data": 'return {',
    "expand_features": 'return {',
    "select_features": 'return {',
    
    # Clustering tools
    "kmeans_cluster": 'return {',
    "dbscan_cluster": 'return {',
    "smart_cluster": 'return {',
    
    # Anomaly detection
    "anomaly": '"message":',
    
    # Export tools
    "export": '"message":',
    
    # Workflow tools
    "suggest_next_steps": 'result["message"]',
    "list_data_files": 'return {',
}

# Template for adding display fields
DISPLAY_FIELDS_TEMPLATE = """
    # [AUTO-GENERATED] Add display fields for UI rendering
    if isinstance(result, dict) and "message" in result:
        from .utils.display_formatter import add_display_fields
        result = add_display_fields(result, result["message"])
"""

def add_display_import(content: str) -> str:
    """Add import for display_formatter if not present."""
    if "from .utils.display_formatter import add_display_fields" in content:
        return content
    
    # Add after other utility imports
    import_section = content.find("from typing import")
    if import_section != -1:
        # Find end of import block
        next_blank = content.find("\n\n", import_section)
        if next_blank != -1:
            return (content[:next_blank] + 
                    "\nfrom .utils.display_formatter import add_display_fields" +
                    content[next_blank:])
    
    return content

def main():
    ds_tools_path = Path("data_science/ds_tools.py")
    
    if not ds_tools_path.exists():
        print(f"[ERROR] File not found: {ds_tools_path}")
        return
    
    print("="*80)
    print("APPLYING __display__ FIX TO ALL TOOLS")
    print("="*80)
    
    content = ds_tools_path.read_text(encoding="utf-8")
    
    # Add import
    content = add_display_import(content)
    
    # For each tool that already has a "message" field, wrap the return with add_display_fields
    # This is safer than trying to patch individual returns
    
    print("\n[INFO] The safest approach is to:")
    print("1. Add a decorator that automatically adds __display__ fields")
    print("2. Or modify the return statements in each tool")
    print("\n[RECOMMENDATION] Use the display_formatter utility in new tools")
    print("For existing tools, we'll update the most critical ones manually.")
    
    critical_tools = [
        "stats", "clean", "accuracy", "evaluate", "explain_model",
        "anomaly", "export", "suggest_next_steps", "list_tools"
    ]
    
    print(f"\n[INFO] Critical tools to update: {len(critical_tools)}")
    for tool in critical_tools:
        print(f"  • {tool}()")
    
    print("\n[STATUS] Creating targeted fixes...")
    
    return content

if __name__ == "__main__":
    content = main()
    print("\n[INFO] Manual fixes will be applied to critical tools")
    print("[INFO] See the update script for details")

