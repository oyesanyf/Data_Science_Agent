#!/usr/bin/env python3
"""
Master Test Runner
Runs all test files and reports results
"""

import subprocess
import sys
from pathlib import Path

def run_test_file(test_file: str) -> tuple[bool, str]:
    """Run a test file and return (success, output)"""
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        success = result.returncode == 0
        
        return success, output
    except subprocess.TimeoutExpired:
        return False, "TEST TIMEOUT (30s exceeded)"
    except Exception as e:
        return False, f"TEST ERROR: {e}"


def main():
    print("\n" + "=" * 80)
    print("RUNNING ALL DATA SCIENCE AGENT TESTS")
    print("=" * 80)
    
    test_files = [
        "test_dataset_naming.py",
        "test_workflow_stages.py",
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = Path(__file__).parent / test_file
        
        if not test_path.exists():
            print(f"\n❌ Test file not found: {test_file}")
            results[test_file] = (False, "File not found")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print("=" * 80)
        
        success, output = run_test_file(str(test_path))
        results[test_file] = (success, output)
        
        # Print output
        print(output)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed_count = sum(1 for success, _ in results.values() if success)
    failed_count = len(results) - passed_count
    
    for test_file, (success, _) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"[{status}] - {test_file}")
    
    print("\n" + "=" * 80)
    print(f"Total: {passed_count} passed, {failed_count} failed")
    print("=" * 80)
    
    if failed_count > 0:
        print("\nSOME TESTS FAILED")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()

