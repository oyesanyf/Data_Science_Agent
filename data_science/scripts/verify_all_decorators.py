"""Verify @ensure_display_fields coverage across all tool files."""
import re
from pathlib import Path
from collections import defaultdict

TOOL_FILES = [
    "data_science/ds_tools.py",
    "data_science/extended_tools.py",
    "data_science/deep_learning_tools.py",
    "data_science/chunk_aware_tools.py",
    "data_science/auto_sklearn_tools.py",
    "data_science/autogluon_tools.py",
    "data_science/advanced_tools.py",
    "data_science/unstructured_tools.py",
    "data_science/utils_tools.py",
    "data_science/advanced_modeling_tools.py",
    "data_science/inference_tools.py",
    "data_science/statistical_tools.py",
    "data_science/utils/artifacts_tools.py",
]

def analyze_file(file_path: Path):
    """Count functions and decorator coverage in a file."""
    if not file_path.exists():
        return None
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    total_funcs = 0
    funcs_with_decorator = 0
    missing = []
    
    for i, line in enumerate(lines):
        match = re.match(r'^(async )?def ([a-z_][a-z0-9_]*)\(', line)
        if match:
            func_name = match.group(2)
            # Skip private functions
            if func_name.startswith('_'):
                continue
            
            total_funcs += 1
            
            # Check if decorator exists
            has_decorator = False
            if i > 0 and '@ensure_display_fields' in lines[i-1]:
                has_decorator = True
                funcs_with_decorator += 1
            
            if not has_decorator:
                missing.append(func_name)
    
    return {
        'total': total_funcs,
        'with_decorator': funcs_with_decorator,
        'missing': missing
    }

def main():
    print("=" * 80)
    print("VERIFYING @ensure_display_fields DECORATOR COVERAGE")
    print("=" * 80)
    
    grand_total = 0
    grand_with_decorator = 0
    all_missing = []
    
    for file_path_str in TOOL_FILES:
        file_path = Path(file_path_str)
        result = analyze_file(file_path)
        
        if result is None:
            print(f"\n[SKIP] {file_path.name} - not found")
            continue
        
        print(f"\n[FILE] {file_path.name}")
        print(f"  Total functions: {result['total']}")
        print(f"  With decorator: {result['with_decorator']}")
        print(f"  Coverage: {result['with_decorator']/result['total']*100 if result['total'] > 0 else 0:.1f}%")
        
        if result['missing']:
            print(f"  MISSING: {', '.join(result['missing'][:5])}")
            if len(result['missing']) > 5:
                print(f"           ... and {len(result['missing'])-5} more")
            all_missing.extend([(file_path.name, fn) for fn in result['missing']])
        
        grand_total += result['total']
        grand_with_decorator += result['with_decorator']
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total public functions across all files: {grand_total}")
    print(f"Functions with @ensure_display_fields: {grand_with_decorator}")
    print(f"Functions WITHOUT decorator: {grand_total - grand_with_decorator}")
    print(f"Overall coverage: {grand_with_decorator/grand_total*100 if grand_total > 0 else 0:.1f}%")
    
    if all_missing:
        print(f"\n[WARNING] {len(all_missing)} functions still missing decorators:")
        for file_name, func_name in all_missing[:20]:
            print(f"  - {file_name}: {func_name}()")
        if len(all_missing) > 20:
            print(f"  ... and {len(all_missing)-20} more")
    else:
        print("\n[SUCCESS] ALL functions have @ensure_display_fields decorator!")
    
    print("=" * 80)

if __name__ == "__main__":
    main()

