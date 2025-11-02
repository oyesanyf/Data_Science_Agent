"""
Script to remove DataFrame type annotations from function signatures.
This fixes Google ADK's automatic function calling schema parsing issues.

Changes:
  def func(df: pd.DataFrame, ...) → def func(df, ...)
  def func(df: DataFrame, ...) → def func(df, ...)
"""
import re
import os
from pathlib import Path

# Tool files that have DataFrame parameters
TOOL_FILES = [
    'data_science/gbm_tools.py',
    'data_science/imbalance_tools.py',
    'data_science/pyod_tools.py',
    'data_science/ts_advanced_tools.py',
    'data_science/river_tools.py',
    'data_science/statsmodels_tools.py',
    'data_science/pymc_tools.py',
    'data_science/lime_tools.py',
    'data_science/ds_tools.py',
    'data_science/autogluon_tools.py',
    'data_science/error_correction.py',
]

def remove_df_type_annotation(content):
    """Remove type annotations from df parameters."""
    
    # Pattern 1: df: pd.DataFrame
    content = re.sub(r'\bdf:\s*pd\.DataFrame\b', 'df', content)
    
    # Pattern 2: df: DataFrame
    content = re.sub(r'\bdf:\s*DataFrame\b', 'df', content)
    
    # Pattern 3: df: pandas.DataFrame
    content = re.sub(r'\bdf:\s*pandas\.DataFrame\b', 'df', content)
    
    # Pattern 4: df: "pd.DataFrame" (string annotations)
    content = re.sub(r'\bdf:\s*["\']pd\.DataFrame["\']\b', 'df', content)
    
    # Pattern 5: df: "DataFrame" (string annotations)
    content = re.sub(r'\bdf:\s*["\']DataFrame["\']\b', 'df', content)
    
    return content

def process_file(filepath):
    """Process a single file to remove DataFrame type annotations."""
    if not os.path.exists(filepath):
        print(f"[WARNING]  SKIP: {filepath} (file not found)")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        modified_content = remove_df_type_annotation(original_content)
        
        if original_content != modified_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"[OK] FIXED: {filepath}")
            return True
        else:
            print(f"ℹ  OK: {filepath} (no changes needed)")
            return False
    except Exception as e:
        print(f"[X] ERROR: {filepath} - {e}")
        return False

def main():
    print("=" * 70)
    print("Removing DataFrame Type Annotations from Tool Files")
    print("=" * 70)
    print()
    
    fixed_count = 0
    for filepath in TOOL_FILES:
        if process_file(filepath):
            fixed_count += 1
    
    print()
    print("=" * 70)
    print(f"[OK] COMPLETE: Fixed {fixed_count} file(s)")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart your server: python start_server.py")
    print("2. Test that tools work without schema errors")
    print("3. The artifact routing wrapper will inject DataFrames automatically")

if __name__ == "__main__":
    main()

