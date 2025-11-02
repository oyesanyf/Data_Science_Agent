"""
Helper script to initialize workspace for existing datasets.
Run this to create workspace structure for datasets that were uploaded before workspace system was implemented.
"""
import os
import sys
from pathlib import Path

# Add data_science to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_science'))

from artifact_manager import ensure_workspace, derive_dataset_slug
from large_data_config import UPLOAD_ROOT

def init_workspace(dataset_name: str):
    """Initialize workspace for a dataset."""
    # Create a minimal state dict
    state = {
        "original_dataset_name": dataset_name
    }
    
    # Create workspace
    workspace = ensure_workspace(state, UPLOAD_ROOT)
    
    print(f"[OK] Workspace created for '{dataset_name}':")
    print(f"   Path: {workspace}")
    print(f"   Subdirectories:")
    for subdir in ["uploads", "plots", "models", "reports", "data", "metrics", "indexes", "logs", "tmp", "manifests"]:
        print(f"     - {subdir}/")
    
    print(f"\n Workspace paths stored in state:")
    for key, value in state.get("workspace_paths", {}).items():
        print(f"   {key}: {value}")
    
    return workspace, state

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init_workspace_for_dataset.py <dataset_name>")
        print("Example: python init_workspace_for_dataset.py tips")
        sys.exit(1)
    
    dataset_name = sys.argv[1]
    workspace, state = init_workspace(dataset_name)
    
    print(f"\n[OK] Done! You can now run tools and they will use this workspace.")
    print(f"\nTo verify:")
    print(f"  dir data_science\\.uploaded\\_workspaces\\{dataset_name}")

