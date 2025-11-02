"""
Safely fix async wrapper calls by adding _run_async() where needed.
"""
import re
from pathlib import Path

# List of async functions that need _run_async wrapper
async_funcs_needing_fix = [
    'scale_data', 'encode_data', 'expand_features', 
    'impute_simple', 'impute_knn', 'impute_iterative',
    'split_data', 'grid_search', 'text_to_features',
    'load_existing_models', 'apply_pca',
    'train_baseline_model', 'train_classifier', 'train_regressor',
    'train_decision_tree', 'train_knn', 'train_naive_bayes', 'train_svm',
    'ensemble', 'explain_model', 'shap_values', 'feature_importance',
    'detect_outliers', 'correlation_analysis', 'create_interactions',
    'handle_outliers', 'polynomial_features', 'train_model',
    'hpo', 'evaluate_model', 'explain_prediction', 'save_model',
    'predict', 'forecast', 'causal_discovery', 'causal_inference',
    'fairness_metrics', 'bias_mitigation', 'drift_detection',
    'data_quality_monitor'
]

wrappers_path = Path("data_science/adk_safe_wrappers.py")
with open(wrappers_path, 'r', encoding='utf-8') as f:
    content = f.read()

fixes = []
for func_name in async_funcs_needing_fix:
    # Pattern: result = func_name(...) without _run_async
    # Should become: result = _run_async(func_name(...))
    
    # Look for: result = func_name(
    pattern = rf'(\n    result = )({func_name}\([^)]+\))'
    
    matches = list(re.finditer(pattern, content))
    for match in matches:
        old_text = match.group(0)
        # Check if _run_async is already there
        if '_run_async' in old_text:
            continue
        
        new_text = f"{match.group(1)}_run_async({match.group(2)})"
        content = content.replace(old_text, new_text, 1)
        fixes.append(f"{func_name}")

# Write back
if fixes:
    with open(wrappers_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {len(fixes)} async function calls:")
    for fix in fixes:
        print(f"  - {fix}")
    print(f"\n[OK] Updated {wrappers_path}")
else:
    print("[INFO] No fixes needed")

