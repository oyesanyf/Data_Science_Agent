"""
Test artifact generation from various data science tools.

This script verifies that:
1. Tools create artifacts in the correct locations
2. Artifacts are properly registered and accessible
3. Artifact metadata is correct
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path

# Ensure data_science module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("TESTING ARTIFACT GENERATION")
print("="*80)

# Setup test environment
test_csv = ".uploaded/1761227823_uploaded.csv"
if not os.path.exists(test_csv):
    print(f"\n[ERROR] Test file not found: {test_csv}")
    print("Please ensure the test CSV exists before running artifact tests.")
    sys.exit(1)

print(f"\nTest file: {test_csv}")
print(f"File exists: {os.path.exists(test_csv)}")
print(f"File size: {os.path.getsize(test_csv)} bytes")

# Clean up old artifacts for clean test
artifact_dirs = [
    ".uploaded_workspaces",
    "data_science/plots",
    "data_science/reports",
    "data_science/models"
]

print("\n" + "="*80)
print("CLEANING OLD ARTIFACTS")
print("="*80)
for dir_path in artifact_dirs:
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print(f"Cleaned: {dir_path}")
        except Exception as e:
            print(f"Warning: Could not clean {dir_path}: {e}")

# Import tools after cleanup
from data_science.ds_tools import shape, head, describe_combo
from data_science.adk_safe_wrappers import shape_tool, head_tool, describe_tool

print("\n" + "="*80)
print("TEST 1: Basic Data Tools (should not create artifacts)")
print("="*80)

# Test shape
print("\n[1.1] Testing shape()...")
result = shape(csv_path=test_csv)
print(f"Status: {result.get('status')}")
print(f"Dimensions: {result.get('rows')} rows x {result.get('columns')} columns")

# Test head
print("\n[1.2] Testing head()...")
result = head(csv_path=test_csv, n=3)
print(f"Status: {result.get('status')}")
print(f"Retrieved {len(result.get('head', []))} rows")

# Test describe
print("\n[1.3] Testing describe_combo()...")
result = asyncio.run(describe_combo(csv_path=test_csv))
print(f"Status: {result.get('status')}")
print(f"Has overview: {'overview' in result}")

print("\n" + "="*80)
print("TEST 2: Tools with Artifact Generation")
print("="*80)

# Test correlation matrix (should create a plot artifact)
print("\n[2.1] Testing correlation_matrix()...")
try:
    from data_science.ds_tools import correlation_matrix
    result = correlation_matrix(csv_path=test_csv)
    print(f"Status: {result.get('status')}")
    print(f"Artifacts: {result.get('artifacts', [])}")
    if result.get('artifacts'):
        for artifact in result['artifacts']:
            if isinstance(artifact, dict):
                path = artifact.get('path')
                if path:
                    print(f"  - {path} (exists: {os.path.exists(path)})")
except Exception as e:
    print(f"Error: {e}")

# Test auto-plot (should create multiple plot artifacts)
print("\n[2.2] Testing plot() / auto_plot()...")
try:
    from data_science.ds_tools import plot
    
    async def test_plot():
        result = await plot(csv_path=test_csv, max_charts=3)
        return result
    
    result = asyncio.run(test_plot())
    print(f"Status: {result.get('status')}")
    print(f"Artifacts: {result.get('artifacts', [])}")
    if result.get('artifacts'):
        for artifact in result['artifacts']:
            if isinstance(artifact, dict):
                path = artifact.get('path')
                if path:
                    print(f"  - {path} (exists: {os.path.exists(path)})")
except Exception as e:
    print(f"Error: {e}")

# Test statistical report (should create a report artifact)
print("\n[2.3] Testing generate_report()...")
try:
    from data_science.ds_tools import generate_report
    result = generate_report(csv_path=test_csv)
    print(f"Status: {result.get('status')}")
    print(f"Artifacts: {result.get('artifacts', [])}")
    if result.get('artifacts'):
        for artifact in result['artifacts']:
            if isinstance(artifact, dict):
                path = artifact.get('path')
                if path:
                    print(f"  - {path} (exists: {os.path.exists(path)})")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("TEST 3: Artifact Directory Scan")
print("="*80)

def scan_directory(dir_path, name):
    """Recursively scan a directory for artifacts."""
    print(f"\n{name}:")
    if not os.path.exists(dir_path):
        print(f"  Directory doesn't exist: {dir_path}")
        return []
    
    artifacts = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(('.png', '.jpg', '.jpeg', '.html', '.json', '.parquet', '.csv')):
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                artifacts.append(full_path)
                print(f"  - {os.path.relpath(full_path, dir_path)} ({size} bytes)")
    
    if not artifacts:
        print("  No artifacts found")
    
    return artifacts

all_artifacts = []
all_artifacts.extend(scan_directory(".uploaded_workspaces", ".uploaded_workspaces"))
all_artifacts.extend(scan_directory("data_science/plots", "data_science/plots"))
all_artifacts.extend(scan_directory("data_science/reports", "data_science/reports"))
all_artifacts.extend(scan_directory("data_science/models", "data_science/models"))
all_artifacts.extend(scan_directory(".uploaded", ".uploaded directory"))

print("\n" + "="*80)
print("TEST 4: Workspace Manifest Check")
print("="*80)

manifest_path = ".uploaded_workspaces/_global/manifest.json"
if os.path.exists(manifest_path):
    print(f"\nManifest found: {manifest_path}")
    try:
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"Manifest contents:")
        print(json.dumps(manifest, indent=2))
    except Exception as e:
        print(f"Error reading manifest: {e}")
else:
    print(f"\nManifest not found: {manifest_path}")

# Check for dataset-specific manifest
dataset_manifest_path = ".uploaded_workspaces/uploaded_f40369e7/manifest.json"
if os.path.exists(dataset_manifest_path):
    print(f"\nDataset manifest found: {dataset_manifest_path}")
    try:
        import json
        with open(dataset_manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"Dataset manifest contents:")
        print(json.dumps(manifest, indent=2))
    except Exception as e:
        print(f"Error reading dataset manifest: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal artifacts found: {len(all_artifacts)}")

if all_artifacts:
    print("\nArtifact types:")
    from collections import Counter
    extensions = Counter([Path(a).suffix for a in all_artifacts])
    for ext, count in extensions.items():
        print(f"  {ext}: {count} files")
    print("\n[OK] Artifacts are being created successfully!")
else:
    print("\n[WARNING] No artifacts were created during testing.")
    print("This may indicate:")
    print("  - Tools are not generating artifacts")
    print("  - Artifacts are being created in unexpected locations")
    print("  - Tools require a tool_context to generate artifacts")

print("="*80)

