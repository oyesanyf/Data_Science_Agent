"""
Quick test to verify model organization and timestamp functionality.
Run this to ensure models are saved correctly with timestamps.
"""

import os
import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_science.ds_tools import (
    _get_project_name,
    _get_model_dir,
    _get_timestamped_model_path,
    MODELS_DIR
)

from data_science.autogluon_tools import _get_autogluon_model_path


def test_project_name_extraction():
    """Test project name extraction from CSV paths."""
    print("\n" + "="*60)
    print("TEST 1: Project Name Extraction")
    print("="*60)
    
    test_cases = [
        ("housing_data.csv", "housing_data"),
        ("sales-2024.csv", "sales-2024"),
        ("my_dataset!@#.csv", "my_dataset___"),
        ("/path/to/iris.csv", "iris"),
        ("C:\\data\\test.csv", "test"),
    ]
    
    for csv_path, expected in test_cases:
        result = _get_project_name(csv_path=csv_path)
        status = "[OK] PASS" if result == expected else f"[X] FAIL (got '{result}')"
        print(f"  {csv_path:<30} → {result:<20} {status}")
    
    print()


def test_model_directory_creation():
    """Test model directory creation."""
    print("="*60)
    print("TEST 2: Model Directory Creation")
    print("="*60)
    
    test_project = "test_housing_data"
    model_dir = _get_model_dir(dataset_name=test_project)
    
    print(f"  Project Name: {test_project}")
    print(f"  Model Dir: {model_dir}")
    print(f"  Expected: {os.path.join(MODELS_DIR, test_project)}")
    
    # Verify directory was created
    if os.path.exists(model_dir):
        print(f"  [OK] PASS: Directory created successfully")
    else:
        print(f"  [X] FAIL: Directory not created")
    
    # Verify it's in the right location
    expected_path = os.path.join(MODELS_DIR, test_project)
    if os.path.normpath(model_dir) == os.path.normpath(expected_path):
        print(f"  [OK] PASS: Directory in correct location")
    else:
        print(f"  [X] FAIL: Wrong location")
    
    print()


def test_timestamped_model_paths():
    """Test timestamped model path generation."""
    print("="*60)
    print("TEST 3: Timestamped Model Paths")
    print("="*60)
    
    test_project = "test_sales_data"
    
    # Generate 3 paths
    paths = []
    for i in range(3):
        path = _get_timestamped_model_path(
            dataset_name=test_project,
            model_type="baseline_model",
            extension=".joblib"
        )
        paths.append(path)
        print(f"  Path {i+1}: {os.path.basename(path)}")
        
        # Small delay to ensure different timestamps
        if i < 2:
            time.sleep(0.1)
    
    # Verify all paths are unique
    unique_paths = len(set(paths))
    if unique_paths == 3:
        print(f"\n  [OK] PASS: All 3 paths are unique")
    else:
        print(f"\n  [X] FAIL: Only {unique_paths} unique paths")
    
    # Verify format: model_type_YYYYMMDD_HHMMSS_xxxx.joblib
    import re
    pattern = r"baseline_model_\d{8}_\d{6}_[0-9a-f]{4}\.joblib"
    
    all_match = all(re.match(pattern, os.path.basename(p)) for p in paths)
    if all_match:
        print(f"  [OK] PASS: All paths match expected format")
    else:
        print(f"  [X] FAIL: Some paths don't match format")
    
    print()


def test_autogluon_paths():
    """Test AutoGluon model path generation."""
    print("="*60)
    print("TEST 4: AutoGluon Model Paths")
    print("="*60)
    
    test_project = "test_iris_data"
    
    # Generate paths for different model types
    model_types = [
        "autogluon_tabular",
        "autogluon_timeseries",
        "autogluon_multimodal",
        "autogluon_hpo"
    ]
    
    for model_type in model_types:
        path = _get_autogluon_model_path(
            dataset_name=test_project,
            model_type=model_type
        )
        dirname = os.path.basename(path)
        print(f"  {model_type:<25} → {dirname}")
        
        # Verify directory was created
        if os.path.exists(path):
            print(f"    [OK] Directory created")
        else:
            print(f"    [X] Directory not created")
    
    print()


def test_directory_structure():
    """Test the overall directory structure."""
    print("="*60)
    print("TEST 5: Overall Directory Structure")
    print("="*60)
    
    print(f"  Models Directory: {MODELS_DIR}")
    print(f"  Exists: {os.path.exists(MODELS_DIR)}")
    
    if os.path.exists(MODELS_DIR):
        print(f"\n  Contents of {MODELS_DIR}:")
        try:
            for item in sorted(os.listdir(MODELS_DIR)):
                item_path = os.path.join(MODELS_DIR, item)
                if os.path.isdir(item_path):
                    # Count models in this project
                    models = [f for f in os.listdir(item_path) 
                             if f.endswith('.joblib') or os.path.isdir(os.path.join(item_path, f))]
                    print(f"     {item}/ ({len(models)} model(s))")
                    for model in models[:3]:  # Show first 3
                        print(f"      - {model}")
                    if len(models) > 3:
                        print(f"      ... and {len(models)-3} more")
        except Exception as e:
            print(f"    [X] Error listing: {e}")
    
    print()


def cleanup_test_data():
    """Clean up test directories."""
    print("="*60)
    print("CLEANUP: Removing Test Data")
    print("="*60)
    
    test_projects = [
        "test_housing_data",
        "test_sales_data",
        "test_iris_data"
    ]
    
    import shutil
    for project in test_projects:
        project_dir = os.path.join(MODELS_DIR, project)
        if os.path.exists(project_dir):
            try:
                shutil.rmtree(project_dir)
                print(f"  [OK] Removed {project}/")
            except Exception as e:
                print(f"  [X] Failed to remove {project}/: {e}")
        else:
            print(f"  [WARNING] {project}/ not found (already clean)")
    
    print()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MODEL ORGANIZATION & TIMESTAMP TESTS")
    print("="*60)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Models Dir: {MODELS_DIR}")
    print()
    
    try:
        # Run tests
        test_project_name_extraction()
        test_model_directory_creation()
        test_timestamped_model_paths()
        test_autogluon_paths()
        test_directory_structure()
        
        print("="*60)
        print("[OK] ALL TESTS COMPLETED")
        print("="*60)
        print()
        
        # Ask before cleanup
        print("Clean up test data? (Y/n): ", end="")
        response = input().strip().lower()
        if response in ("", "y", "yes"):
            cleanup_test_data()
        else:
            print("\nTest data preserved in data_science/models/")
            print("Run cleanup_test_data() manually to remove.\n")
        
    except Exception as e:
        print(f"\n[X] TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

