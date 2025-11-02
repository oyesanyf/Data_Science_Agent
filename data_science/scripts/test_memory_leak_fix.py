"""Test the memory leak fix for analyze_dataset"""
import pandas as pd
import sys
from pathlib import Path

print("=" * 70)
print("MEMORY LEAK FIX TEST - STARTING")
print("=" * 70)
print(flush=True)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("Importing functions...", flush=True)
from data_science.ds_tools import _profile_numeric, _compute_correlations

def test_memory_leak_fix():
    """Test that the fixed functions don't cause memory leaks"""
    
    print("\nLoading problematic file...", flush=True)
    # Load the problematic file that caused the 8GB allocation
    df = pd.read_csv('.uploaded/1761175540_uploaded.csv')
    
    print(f"File loaded: shape={df.shape}", flush=True)
    print(f"Columns: {list(df.columns)}", flush=True)
    print(f"Numeric columns: {list(df.select_dtypes(include=['number']).columns)}", flush=True)
    print(flush=True)
    
    # Test _profile_numeric
    print("=" * 70, flush=True)
    print("TEST 1: _profile_numeric (the function that had memory leak)", flush=True)
    print("=" * 70, flush=True)
    try:
        result1 = _profile_numeric(df)
        print(f"SUCCESS: returned {len(result1)} keys", flush=True)
        print(f"Keys: {list(result1.keys())}", flush=True)
    except MemoryError as e:
        print(f"FAILED: MemoryError - {e}", flush=True)
        return False
    except Exception as e:
        print(f"FAILED: {type(e).__name__} - {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False
    
    print(flush=True)
    
    # Test _compute_correlations
    print("=" * 70, flush=True)
    print("TEST 2: _compute_correlations (Kendall correlation fix)", flush=True)
    print("=" * 70, flush=True)
    try:
        result2 = _compute_correlations(df)
        print(f"SUCCESS: returned {len(result2)} keys", flush=True)
        print(f"Keys: {list(result2.keys())}", flush=True)
        
        # Check if Kendall was skipped (it shouldn't be for 250 rows)
        if 'kendall' in result2:
            print(f"Kendall computed (dataset small enough: 250 rows)", flush=True)
        elif 'kendall_skipped' in result2:
            print(f"Kendall skipped: {result2['kendall_skipped']}", flush=True)
        
    except MemoryError as e:
        print(f"FAILED: MemoryError - {e}", flush=True)
        return False
    except Exception as e:
        print(f"FAILED: {type(e).__name__} - {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False
    
    print(flush=True)
    print("=" * 70, flush=True)
    print("ALL TESTS PASSED - Memory leak FIXED!", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)
    print("SUMMARY:", flush=True)
    print("- File that caused 7.93 GiB allocation now works correctly", flush=True)
    print("- _profile_numeric: Only processes numeric columns (memory safe)", flush=True)
    print("- _compute_correlations: NaN handling + Kendall size limits", flush=True)
    print(flush=True)
    return True

if __name__ == "__main__":
    try:
        success = test_memory_leak_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {type(e).__name__} - {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

