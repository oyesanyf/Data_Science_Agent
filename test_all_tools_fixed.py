"""
Test script to verify ALL tools now show real results.
"""

# Add data_science to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "data_science"))

from adk_safe_wrappers import _ensure_ui_display

def test_analyze_dataset():
    """Test analyze_dataset_tool result extraction."""
    test_result = {
        'status': 'success',
        'result': {
            'overview': {
                'shape': {'rows': 1000, 'cols': 10},
                'columns': ['A', 'B', 'C', 'D', 'E'],
                'memory_usage': '80 KB'
            },
            'numeric_summary': {
                'A': {'mean': 5.2, 'std': 1.3},
                'B': {'mean': 10.5, 'std': 2.1}
            },
            'categorical_summary': {
                'C': {'unique_count': 5, 'top_value': 'Yes'}
            },
            'correlations': {
                'strong': [
                    {'col1': 'A', 'col2': 'B', 'correlation': 0.85}
                ]
            },
            'outliers': {
                'A': {'count': 3}
            }
        }
    }
    
    result = _ensure_ui_display(test_result, 'analyze_dataset', None)
    
    print("=== TEST 1: analyze_dataset_tool ===")
    print(f"✓ Result has __display__: {bool(result.get('__display__'))}")
    print(f"✓ Display length: {len(result.get('__display__', ''))} chars")
    
    display = result.get('__display__', '')
    checks = {
        'Has Shape info': 'Shape:' in display,
        'Has Numeric Features': 'Numeric Features' in display,
        'Has Categorical Features': 'Categorical Features' in display,
        'Has Correlations': 'Correlations' in display,
        'Has Outliers': 'Outliers' in display,
        'Shows actual data': 'mean=' in display,
        'NOT generic message': 'completed successfully' not in display
    }
    
    for check, passed in checks.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {check}")
    
    print(f"\n__display__ preview (first 400 chars):")
    print(display[:400])
    print(f"\n{'='*60}\n")
    
    return all(checks.values())


def test_train_classifier():
    """Test train_classifier_tool result extraction."""
    test_result = {
        'status': 'success',
        'result': {
            'model': 'RandomForest',
            'metrics': {
                'accuracy': 0.8537,
                'precision': 0.8421,
                'recall': 0.8654,
                'f1': 0.8536,
                'roc_auc': 0.9123
            },
            'artifacts': ['model.joblib', 'confusion_matrix.png']
        }
    }
    
    result = _ensure_ui_display(test_result, 'train_classifier', None)
    
    print("=== TEST 2: train_classifier_tool ===")
    print(f"✓ Result has __display__: {bool(result.get('__display__'))}")
    print(f"✓ Display length: {len(result.get('__display__', ''))} chars")
    
    display = result.get('__display__', '')
    checks = {
        'Has Metrics': 'Metrics:' in display or 'accuracy' in display,
        'Shows accuracy value': '0.8537' in display,
        'Shows artifacts': 'Artifacts' in display or 'model.joblib' in display,
        'NOT generic message': 'completed successfully' not in display
    }
    
    for check, passed in checks.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {check}")
    
    print(f"\n__display__ preview (first 400 chars):")
    print(display[:400])
    print(f"\n{'='*60}\n")
    
    return all(checks.values())


def test_plot_tool():
    """Test plot_tool result extraction."""
    test_result = {
        'status': 'success',
        'result': {
            'plots': [
                'correlation.png',
                'distribution_A.png',
                'boxplot.png'
            ]
        },
        'artifacts': ['correlation.png', 'distribution_A.png', 'boxplot.png']
    }
    
    result = _ensure_ui_display(test_result, 'plot', None)
    
    print("=== TEST 3: plot_tool ===")
    print(f"✓ Result has __display__: {bool(result.get('__display__'))}")
    print(f"✓ Display length: {len(result.get('__display__', ''))} chars")
    
    display = result.get('__display__', '')
    checks = {
        'Shows artifacts': 'Artifacts' in display or '.png' in display,
        'Lists plot files': 'correlation.png' in display,
        'NOT generic message': 'completed successfully' not in display
    }
    
    for check, passed in checks.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {check}")
    
    print(f"\n__display__ preview (first 400 chars):")
    print(display[:400])
    print(f"\n{'='*60}\n")
    
    return all(checks.values())


def test_generic_tool():
    """Test a tool with simple result."""
    test_result = {
        'status': 'success',
        'message': 'Operation completed with 5 items processed'
    }
    
    result = _ensure_ui_display(test_result, 'generic_tool', None)
    
    print("=== TEST 4: generic_tool (simple result) ===")
    print(f"✓ Result has __display__: {bool(result.get('__display__'))}")
    print(f"✓ Display length: {len(result.get('__display__', ''))} chars")
    
    display = result.get('__display__', '')
    checks = {
        'Has display': bool(display),
        'Shows message': 'completed with 5 items' in display
    }
    
    for check, passed in checks.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {check}")
    
    print(f"\n__display__: {display}")
    print(f"\n{'='*60}\n")
    
    return all(checks.values())


if __name__ == "__main__":
    print("\n" + "="*60)
    print(" TESTING ALL TOOLS FIXED - UNIVERSAL DATA EXTRACTION")
    print("="*60 + "\n")
    
    results = {
        'analyze_dataset': test_analyze_dataset(),
        'train_classifier': test_train_classifier(),
        'plot': test_plot_tool(),
        'generic': test_generic_tool()
    }
    
    print("\n" + "="*60)
    print(" FINAL RESULTS")
    print("="*60)
    
    for tool, passed in results.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {tool}_tool: {'PASSED' if passed else 'FAILED'}")
    
    all_passed = all(results.values())
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL TESTS PASSED - ALL TOOLS NOW SHOW REAL RESULTS!")
    else:
        print("⚠️ Some tests failed - review above output")
    print(f"{'='*60}\n")
    
    sys.exit(0 if all_passed else 1)

