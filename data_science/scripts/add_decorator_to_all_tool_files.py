"""
Add @ensure_display_fields decorator to ALL tools in ALL tool files.
Comprehensive fix for entire codebase.
"""
import re
from pathlib import Path

# All tool files in the codebase
TOOL_FILES = [
    "data_science/ds_tools.py",
    "data_science/utils/artifacts_tools.py",
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
]

def add_decorator_to_file(file_path: Path, decorator_name: str = "@ensure_display_fields"):
    """Add decorator to all async def and def functions that return dict."""
    
    if not file_path.exists():
        print(f"[SKIP] File not found: {file_path}")
        return 0
    
    print(f"\n[PROCESSING] {file_path.name}")
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Check if decorator is already defined or imported
    has_decorator = False
    for line in lines:
        if 'ensure_display_fields' in line and ('def ' in line or 'import' in line):
            has_decorator = True
            break
    
    if not has_decorator and file_path.name != 'ds_tools.py':
        # Add import at the top (after other imports)
        import_line = "from .ds_tools import ensure_display_fields"
        if file_path.name in ['artifacts_tools.py', 'paths.py', 'io.py']:
            import_line = "from ..ds_tools import ensure_display_fields"
        
        # Find where to insert import
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i + 1
            elif line.strip() == '' and insert_idx > 0:
                break
        
        if insert_idx > 0:
            lines.insert(insert_idx, import_line)
            print(f"  [+] Added import: {import_line}")
    
    modified_lines = []
    i = 0
    decorators_added = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a function definition
        match = re.match(r'^(async )?def ([a-z_][a-z0-9_]*)\(', line)
        
        if match:
            func_name = match.group(2)
            
            # Skip private functions and special methods
            if func_name.startswith('_') or func_name in ['__init__', '__str__', '__repr__']:
                modified_lines.append(line)
                i += 1
                continue
            
            # Check if decorator already exists
            has_decorator = False
            if i > 0:
                prev_line = lines[i-1].strip()
                if '@ensure_display_fields' in prev_line or '@' in prev_line:
                    has_decorator = True
            
            if not has_decorator:
                # Get indentation
                indent = len(line) - len(line.lstrip())
                decorator_line = ' ' * indent + '@ensure_display_fields'
                modified_lines.append(decorator_line)
                decorators_added += 1
                print(f"  [+] {func_name}()")
        
        modified_lines.append(line)
        i += 1
    
    if decorators_added > 0:
        # Write back
        new_content = '\n'.join(modified_lines)
        file_path.write_text(new_content, encoding='utf-8')
        print(f"  [OK] Added {decorators_added} decorators to {file_path.name}")
    else:
        print(f"  [OK] All decorators already present in {file_path.name}")
    
    return decorators_added

def main():
    print("="*80)
    print("ADDING @ensure_display_fields TO ALL TOOLS IN ENTIRE CODEBASE")
    print("="*80)
    
    total_decorators = 0
    files_modified = 0
    
    for file_path_str in TOOL_FILES:
        file_path = Path(file_path_str)
        count = add_decorator_to_file(file_path)
        total_decorators += count
        if count > 0:
            files_modified += 1
    
    print("\n" + "="*80)
    print(f"COMPLETE!")
    print(f"  Files modified: {files_modified}/{len(TOOL_FILES)}")
    print(f"  Total decorators added: {total_decorators}")
    print("="*80)
    print("\n[NEXT] Restart server to apply changes:")
    print("  cd C:\\harfile\\data_science_agent")
    print("  taskkill /F /IM python.exe")
    print("  python start_server.py")

if __name__ == "__main__":
    main()

