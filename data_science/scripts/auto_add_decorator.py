"""
Automatically add @ensure_display_fields decorator to all tools in ds_tools.py
"""
import re
from pathlib import Path

def add_decorators_to_file(file_path: Path):
    """Add @ensure_display_fields to all async/sync functions that return dict."""
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Tools that should get the decorator (return dict and are user-facing)
    # Skip private functions (_funcname) and utility functions
    tools_to_decorate = [
        'describe_combo', 'train_baseline_model', 'auto_analyze_and_model',
        'suggest_next_steps', 'list_data_files', 'plot', 'predict',
        'classify', 'train', 'train_classifier', 'train_regressor',
        'train_decision_tree', 'recommend_model', 'train_knn',
        'train_naive_bayes', 'train_svm', 'apply_pca', 'load_model',
        'kmeans_cluster', 'dbscan_cluster', 'hierarchical_cluster',
        'isolation_forest_train', 'smart_cluster', 'scale_data',
        'encode_data', 'expand_features', 'impute_simple', 'impute_knn',
        'impute_iterative', 'select_features', 'recursive_select',
        'sequential_select', 'split_data', 'grid_search', 'evaluate',
        'text_to_features', 'anomaly', 'accuracy', 'load_existing_models',
        'ensemble', 'clean', 'explain_model', 'export_executive_report',
        'export', 'save_uploaded_file', 'execute_next_step', 'maintenance',
    ]
    
    modified_lines = []
    i = 0
    decorators_added = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a function definition
        match = re.match(r'^(async )?def ([a-z_][a-z0-9_]*)\(', line)
        
        if match:
            func_name = match.group(2)
            
            # Check if it's in our list and doesn't already have the decorator
            if func_name in tools_to_decorate:
                # Look back to see if decorator already exists
                has_decorator = False
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line == '@ensure_display_fields':
                        has_decorator = True
                
                if not has_decorator:
                    # Get indentation
                    indent = len(line) - len(line.lstrip())
                    decorator_line = ' ' * indent + '@ensure_display_fields'
                    modified_lines.append(decorator_line)
                    decorators_added += 1
                    print(f"[OK] Added decorator to: {func_name}()")
        
        modified_lines.append(line)
        i += 1
    
    if decorators_added > 0:
        # Write back
        new_content = '\n'.join(modified_lines)
        file_path.write_text(new_content, encoding='utf-8')
        print(f"\n[SUCCESS] Added {decorators_added} decorators to ds_tools.py")
    else:
        print("\n[OK] All decorators already present!")
    
    return decorators_added

if __name__ == "__main__":
    ds_tools_path = Path("data_science/ds_tools.py")
    
    print("="*80)
    print("ADDING @ensure_display_fields TO ALL TOOLS")
    print("="*80)
    print()
    
    if not ds_tools_path.exists():
        print(f"[ERROR] File not found: {ds_tools_path}")
        exit(1)
    
    count = add_decorators_to_file(ds_tools_path)
    
    print("\n" + "="*80)
    print(f"COMPLETE: {count} decorators added")
    print("="*80)
    print("\n[TIP] Restart the server to apply changes:")
    print("   python start_server.py")

