#!/usr/bin/env python3
"""
Test Dataset Naming Logic
Tests that dataset names are correctly extracted from filenames and display_name
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_derive_dataset_slug():
    """Test dataset slug extraction with various inputs"""
    from artifact_manager import derive_dataset_slug
    
    print("=" * 80)
    print("TEST 1: Dataset Name Extraction")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        {
            "name": "Display name with original filename",
            "state": {},
            "display_name": "car_crashes.csv",
            "filepath": "C:/harfile/.uploaded/1761964200_uploaded.csv",
            "headers": ["total", "speeding", "alcohol", "not_distracted"],
            "expected": "car_crashes"
        },
        {
            "name": "Filepath with timestamp prefix",
            "state": {},
            "display_name": None,
            "filepath": "C:/harfile/.uploaded/1761964200_customer_data.csv",
            "headers": ["name", "age", "salary"],
            "expected": "customer_data"
        },
        {
            "name": "Headers-based naming (meaningful columns)",
            "state": {},
            "display_name": None,
            "filepath": "C:/harfile/.uploaded/1761964200_uploaded.csv",
            "headers": ["total", "speeding", "alcohol"],
            "expected": "total_speeding"
        },
        {
            "name": "Generic filename falls back to headers",
            "state": {},
            "display_name": "uploaded.csv",
            "filepath": "C:/harfile/.uploaded/uploaded_1234567890_uploaded.csv",
            "headers": ["sales", "revenue", "profit"],
            "expected": "sales_revenue"
        },
        {
            "name": "Complete fallback to 'uploaded'",
            "state": {},
            "display_name": None,
            "filepath": None,
            "headers": None,
            "expected": "uploaded"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Input:")
        print(f"     - display_name: {test['display_name']}")
        print(f"     - filepath: {test['filepath']}")
        print(f"     - headers: {test['headers']}")
        
        try:
            result = derive_dataset_slug(
                test['state'],
                display_name=test['display_name'],
                filepath=test['filepath'],
                headers=test['headers']
            )
            
            print(f"   Result: {result}")
            print(f"   Expected: {test['expected']}")
            
            if result == test['expected']:
                print(f"   ✅ PASS")
                passed += 1
            else:
                print(f"   ❌ FAIL - Got '{result}' but expected '{test['expected']}'")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


def test_workspace_path_structure():
    """Test that workspace paths use .uploaded (with dot)"""
    from artifact_manager import ensure_workspace, _get_workspaces_root
    from large_data_config import UPLOAD_ROOT
    from pathlib import Path
    
    print("\n" + "=" * 80)
    print("TEST 2: Workspace Path Structure")
    print("=" * 80)
    
    print(f"\n1. UPLOAD_ROOT Configuration:")
    print(f"   UPLOAD_ROOT = {UPLOAD_ROOT}")
    
    # Check if it ends with .uploaded
    upload_root_str = str(UPLOAD_ROOT)
    has_dot = ".uploaded" in upload_root_str
    print(f"   Contains '.uploaded': {'✅ YES' if has_dot else '❌ NO'}")
    
    if not has_dot:
        print(f"   ❌ FAIL: UPLOAD_ROOT should contain '.uploaded' (with dot)")
        return False
    
    print(f"\n2. Workspaces Root:")
    try:
        workspaces_root = _get_workspaces_root(str(UPLOAD_ROOT))
        print(f"   Workspaces root: {workspaces_root}")
        
        expected_suffix = Path(".uploaded") / "_workspaces"
        actual_path = Path(workspaces_root)
        
        # Check if path contains .uploaded/_workspaces
        path_parts = actual_path.parts
        has_correct_structure = ".uploaded" in path_parts and "_workspaces" in path_parts
        
        print(f"   Contains '.uploaded/_workspaces': {'✅ YES' if has_correct_structure else '❌ NO'}")
        
        if not has_correct_structure:
            print(f"   ❌ FAIL: Workspaces root should be under .uploaded/_workspaces")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False
    
    print(f"\n3. Test Workspace Creation:")
    test_state = {
        "original_dataset_name": "test_dataset",
        "workspace_run_id": "20251101_test"
    }
    
    try:
        workspace_path = ensure_workspace(test_state, UPLOAD_ROOT)
        print(f"   Created workspace: {workspace_path}")
        
        # Check structure
        workspace_str = str(workspace_path)
        checks = {
            "Contains .uploaded": ".uploaded" in workspace_str,
            "Contains _workspaces": "_workspaces" in workspace_str,
            "Contains dataset name": "test_dataset" in workspace_str,
            "Contains run_id": "20251101_test" in workspace_str,
        }
        
        all_passed = True
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        if not all_passed:
            print(f"\n   ❌ FAIL: Workspace structure incorrect")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ All path structure tests PASSED")
    print("=" * 80)
    return True


def test_filename_extraction():
    """Test filename extraction from part.inline_data.display_name"""
    print("\n" + "=" * 80)
    print("TEST 3: Filename Extraction Logic")
    print("=" * 80)
    
    # Simulate the extraction logic from agent.py
    test_cases = [
        {
            "part_attrs": {
                "file_name": None,
                "inline_data": {
                    "file_name": None,
                    "display_name": "car_crashes.csv"
                }
            },
            "expected": "car_crashes.csv"
        },
        {
            "part_attrs": {
                "file_name": "customer_data.csv",
                "inline_data": {
                    "file_name": None,
                    "display_name": None
                }
            },
            "expected": "customer_data.csv"
        },
        {
            "part_attrs": {
                "file_name": None,
                "inline_data": {
                    "file_name": "sales_report.csv",
                    "display_name": None
                }
            },
            "expected": "sales_report.csv"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing extraction priority:")
        
        # Simulate extraction logic
        part = type('obj', (object,), test['part_attrs'])()
        if hasattr(part.inline_data, '__getitem__'):
            # Dict
            inline_data = type('obj', (object,), test['part_attrs']['inline_data'])()
        else:
            inline_data = part.inline_data
        
        part.inline_data = inline_data
        
        # Try extraction (same order as agent.py lines 4139-4147)
        original_filename = None
        if hasattr(part, 'file_name') and part.file_name:
            original_filename = part.file_name
            source = "part.file_name"
        elif hasattr(part.inline_data, 'file_name') and part.inline_data.file_name:
            original_filename = part.inline_data.file_name
            source = "part.inline_data.file_name"
        elif hasattr(part.inline_data, 'display_name') and part.inline_data.display_name:
            original_filename = part.inline_data.display_name
            source = "part.inline_data.display_name"
        
        print(f"   Expected: {test['expected']}")
        print(f"   Got: {original_filename} (from {source if original_filename else 'none'})")
        
        if original_filename == test['expected']:
            print(f"   ✅ PASS")
            passed += 1
        else:
            print(f"   ❌ FAIL")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DATASET NAMING & PATH STRUCTURE TESTS")
    print("=" * 80)
    
    all_passed = True
    
    # Test 1: Dataset naming
    if not test_derive_dataset_slug():
        all_passed = False
    
    # Test 2: Workspace paths
    if not test_workspace_path_structure():
        all_passed = False
    
    # Test 3: Filename extraction
    if not test_filename_extraction():
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        print("=" * 80)
        sys.exit(1)

