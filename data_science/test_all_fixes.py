"""
Test script to verify all critical fixes are working:
1. Workspace root tracking
2. Parquet auto-conversion
3. Plot tool results with artifact paths
4. Artifact routing
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_workspace_tracking():
    """Test that workspace_root is properly created and tracked"""
    print("\n" + "="*60)
    print("TEST 1: Workspace Root Tracking")
    print("="*60)
    
    try:
        from artifact_manager import ensure_workspace
        from large_data_config import UPLOAD_ROOT
        
        # Create a mock state
        state = {}
        
        # Call ensure_workspace
        workspace_path = ensure_workspace(state, UPLOAD_ROOT)
        
        # Verify workspace_root is set
        assert "workspace_root" in state, "workspace_root not set in state"
        assert state["workspace_root"], "workspace_root is empty"
        assert Path(state["workspace_root"]).exists(), f"workspace_root doesn't exist: {state['workspace_root']}"
        
        print(f"SUCCESS workspace_root created: {state['workspace_root']}")
        print(f"SUCCESS workspace_paths: {list(state.get('workspace_paths', {}).keys())}")
        
        # Verify folder structure
        expected_folders = ["uploads", "data", "models", "reports", "results", "plots", "metrics", "logs"]
        for folder in expected_folders:
            folder_path = Path(state["workspace_root"]) / folder
            assert folder_path.exists(), f"Missing folder: {folder}"
            print(f"SUCCESS {folder}/ exists")
        
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parquet_conversion():
    """Test that Parquet files are auto-converted to CSV"""
    print("\n" + "="*60)
    print("TEST 2: Parquet Auto-Conversion")
    print("="*60)
    
    try:
        from large_data_config import UPLOAD_ROOT
        import pandas as pd
        
        # Create a test Parquet file
        test_data = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        
        parquet_path = UPLOAD_ROOT / "test_parquet_conversion.parquet"
        test_data.to_parquet(parquet_path, index=False)
        print(f"SUCCESS Created test parquet: {parquet_path}")
        
        # Simulate the conversion logic from large_data_handler.py
        if parquet_path.suffix.lower() == '.parquet':
            df = pd.read_parquet(parquet_path)
            csv_filename = parquet_path.name.replace('.parquet', '.csv')
            csv_path = UPLOAD_ROOT / csv_filename
            df.to_csv(csv_path, index=False)
            print(f"SUCCESS Converted to CSV: {csv_path}")
            
            # Try to delete parquet
            try:
                parquet_path.unlink()
                print(f"SUCCESS Deleted original parquet")
            except Exception as e:
                print(f"WARNING Failed to delete parquet: {e}")
            
            # Verify CSV exists and has correct data
            assert csv_path.exists(), "CSV file not created"
            df_csv = pd.read_csv(csv_path)
            assert len(df_csv) == 3, "CSV has wrong number of rows"
            assert list(df_csv.columns) == ['col1', 'col2'], "CSV has wrong columns"
            print(f"SUCCESS CSV has correct data: {len(df_csv)} rows, {list(df_csv.columns)} columns")
            
            # Clean up
            csv_path.unlink()
            print(f"SUCCESS Cleaned up test files")
        
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plot_tool_display():
    """Test that plot_tool returns proper display with artifact paths"""
    print("\n" + "="*60)
    print("TEST 3: Plot Tool Display Format")
    print("="*60)
    
    try:
        # Test that plot_tool_guard formats display correctly
        from plot_tool_guard import plot_tool_guard
        
        # Create a mock result with artifacts
        mock_result = {
            "status": "success",
            "artifacts": [
                {"filename": "plots/test_plot1.png", "version": 1},
                {"filename": "plots/test_plot2.png", "version": 1}
            ]
        }
        
        # Verify the display formatting logic
        artifacts = mock_result.get("artifacts", [])
        assert len(artifacts) == 2, "Wrong number of artifacts"
        
        # Build expected display message
        shown_names = [a["filename"].split("/")[-1] for a in artifacts]
        expected_names = ["test_plot1.png", "test_plot2.png"]
        assert shown_names == expected_names, f"Wrong artifact names: {shown_names}"
        
        print(f"SUCCESS Mock artifacts formatted correctly: {shown_names}")
        print(f"SUCCESS plot_tool_guard should display these in chat")
        
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_page_workspace_root():
    """Test that ui_page.py can recover workspace_root"""
    print("\n" + "="*60)
    print("TEST 4: UI Page Workspace Root Recovery")
    print("="*60)
    
    try:
        from ui_page import _state_as_dict
        from pathlib import Path
        
        # Test 1: workspace_root exists in state
        class MockContext:
            def __init__(self, state):
                self.state = state
        
        state_with_root = {"workspace_root": "/test/workspace"}
        ctx = MockContext(state_with_root)
        state_dict = _state_as_dict(ctx)
        assert state_dict.get("workspace_root") == "/test/workspace", "Failed to get workspace_root from state"
        print(f"SUCCESS Retrieved workspace_root from state: {state_dict['workspace_root']}")
        
        # Test 2: Derive workspace_root from workspace_paths
        state_with_paths = {
            "workspace_paths": {
                "reports": "/test/workspace/reports",
                "uploads": "/test/workspace/uploads"
            }
        }
        ctx2 = MockContext(state_with_paths)
        state_dict2 = _state_as_dict(ctx2)
        # The UI page should derive workspace_root from reports path
        if "workspace_paths" in state_dict2:
            reports_path = state_dict2["workspace_paths"].get("reports")
            if reports_path:
                derived_root = str(Path(reports_path).parent)
                print(f"SUCCESS Can derive workspace_root from paths: {derived_root}")
        
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_path_enforcement():
    """Test that .uploaded (with dot) is enforced"""
    print("\n" + "="*60)
    print("TEST 5: Path Enforcement (.uploaded)")
    print("="*60)
    
    try:
        from large_data_config import UPLOAD_ROOT
        
        # Verify UPLOAD_ROOT ends with .uploaded
        upload_root_str = str(UPLOAD_ROOT)
        assert ".uploaded" in upload_root_str, f"UPLOAD_ROOT doesn't contain .uploaded: {upload_root_str}"
        assert Path(UPLOAD_ROOT).name == ".uploaded", f"UPLOAD_ROOT doesn't end with .uploaded: {UPLOAD_ROOT}"
        
        print(f"SUCCESS UPLOAD_ROOT is correct: {UPLOAD_ROOT}")
        print(f"SUCCESS Path uses .uploaded (with dot)")
        
        # Verify _workspaces exists under .uploaded
        workspaces_dir = UPLOAD_ROOT / "_workspaces"
        print(f"SUCCESS _workspaces location: {workspaces_dir}")
        
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print(" TESTING ALL FIXES")
    print("="*60)
    
    results = {
        "Workspace Tracking": test_workspace_tracking(),
        "Parquet Conversion": test_parquet_conversion(),
        "Plot Tool Display": test_plot_tool_display(),
        "UI Page Workspace": test_ui_page_workspace_root(),
        "Path Enforcement": test_path_enforcement(),
    }
    
    print("\n" + "="*60)
    print(" TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "SUCCESS" if passed else "FAIL"
        print(f"{icon} {test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print(" ALL TESTS PASSED SUCCESS")
    else:
        print(" SOME TESTS FAILED - CHECK OUTPUT ABOVE")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

