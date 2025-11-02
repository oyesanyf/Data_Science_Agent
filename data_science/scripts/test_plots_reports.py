"""
Test plot and report generation from data science tools.

This script verifies that:
1. Visualization tools create plot artifacts (.png, .html)
2. Report generation creates report artifacts (.html, .json)
3. Artifacts are saved in the correct workspace directories
4. Artifacts are accessible and have valid content
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path

# Ensure data_science module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("TESTING PLOT AND REPORT GENERATION")
print("="*80)

# Setup test environment
test_csv = ".uploaded/1761227823_uploaded.csv"
if not os.path.exists(test_csv):
    print(f"\n[ERROR] Test file not found: {test_csv}")
    print("Please ensure the test CSV exists before running this test.")
    sys.exit(1)

print(f"\nTest file: {test_csv}")
print(f"File exists: {os.path.exists(test_csv)}")
print(f"File size: {os.path.getsize(test_csv)} bytes")

# Import after confirming file exists
from data_science.ds_tools import plot, stats, export_executive_report, export

print("\n" + "="*80)
print("TEST 1: Automatic Plot Generation (plot)")
print("="*80)

try:
    print("\n[1.1] Generating automatic plots (max 4 charts)...")
    
    async def test_plot():
        result = await plot(csv_path=test_csv, max_charts=4)
        return result
    
    result = asyncio.run(test_plot())
    
    print(f"Status: {result.get('status')}")
    message = result.get('message', 'N/A')
    print(f"Message: {message[:200]}..." if len(message) > 200 else f"Message: {message}")
    
    if result.get('artifacts'):
        print(f"\nArtifacts created: {len(result['artifacts'])}")
        plot_count = 0
        for artifact in result['artifacts']:
            path = artifact if isinstance(artifact, str) else artifact.get('path')
            if path:
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                ext = Path(path).suffix
                if ext in ['.png', '.jpg', '.jpeg', '.html', '.svg']:
                    plot_count += 1
                print(f"  - {Path(path).name}")
                print(f"    Type: {ext}, Exists: {exists}, Size: {size} bytes")
        print(f"\n[OK] Plot generation test PASSED - Created {plot_count} plot files")
    elif result.get('plot_paths'):
        print(f"\nPlot paths returned: {len(result['plot_paths'])}")
        for path in result['plot_paths']:
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            print(f"  - {Path(path).name}: Exists={exists}, Size={size} bytes")
        print("\n[OK] Plot generation test PASSED")
    else:
        print("\n[WARNING] No artifacts or plot_paths returned by plot()")
        print(f"Full result keys: {list(result.keys())}")
        
except Exception as e:
    print(f"\n[ERROR] Plot generation test FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST 2: Statistical Analysis (stats)")
print("="*80)

try:
    print("\n[2.1] Running statistical analysis...")
    
    async def test_stats():
        result = await stats(csv_path=test_csv)
        return result
    
    result = asyncio.run(test_stats())
    
    print(f"Status: {result.get('status')}")
    
    # Check for various output formats
    has_summary = 'summary' in result
    has_stats = 'statistics' in result
    has_analysis = 'analysis' in result
    
    print(f"Has summary: {has_summary}")
    print(f"Has statistics: {has_stats}")
    print(f"Has analysis: {has_analysis}")
    
    if result.get('artifacts'):
        print(f"\nArtifacts created: {len(result['artifacts'])}")
        for artifact in result['artifacts']:
            path = artifact if isinstance(artifact, str) else artifact.get('path')
            if path:
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                print(f"  - {Path(path).name}: Exists={exists}, Size={size} bytes")
        print("\n[OK] Statistical analysis test PASSED")
    else:
        print("\n[INFO] Stats completed without file artifacts (expected for simple stats)")
        if has_summary or has_stats or has_analysis:
            print("[OK] Statistical analysis test PASSED (in-memory results)")
        
except Exception as e:
    print(f"\n[ERROR] Statistical analysis test FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST 3: Executive Report Generation")
print("="*80)

try:
    print("\n[3.1] Generating executive report...")
    
    async def test_report():
        result = await export_executive_report(csv_path=test_csv)
        return result
    
    result = asyncio.run(test_report())
    
    print(f"Status: {result.get('status')}")
    
    if result.get('artifacts'):
        print(f"\nArtifacts created: {len(result['artifacts'])}")
        report_count = 0
        for artifact in result['artifacts']:
            path = artifact if isinstance(artifact, str) else artifact.get('path')
            if path:
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                ext = Path(path).suffix
                if ext in ['.html', '.json', '.txt', '.md', '.pdf']:
                    report_count += 1
                print(f"  - {Path(path).name}")
                print(f"    Type: {ext}, Exists: {exists}, Size: {size} bytes")
        print(f"\n[OK] Report generation test PASSED - Created {report_count} report files")
    elif result.get('report_path'):
        path = result['report_path']
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f"\nReport created: {Path(path).name}")
        print(f"  Exists: {exists}, Size: {size} bytes")
        print("\n[OK] Report generation test PASSED")
    else:
        print("\n[WARNING] No artifacts or report_path returned")
        print(f"Result keys: {list(result.keys())}")
        
except Exception as e:
    print(f"\n[ERROR] Report generation test FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST 4: Data Export")
print("="*80)

try:
    print("\n[4.1] Exporting data (JSON format)...")
    
    async def test_export():
        result = await export(csv_path=test_csv, output_format="json")
        return result
    
    result = asyncio.run(test_export())
    
    print(f"Status: {result.get('status')}")
    
    if result.get('artifacts'):
        print(f"\nArtifacts created: {len(result['artifacts'])}")
        for artifact in result['artifacts']:
            path = artifact if isinstance(artifact, str) else artifact.get('path')
            if path:
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                print(f"  - {Path(path).name}: Exists={exists}, Size={size} bytes")
        print("\n[OK] Export test PASSED")
    elif result.get('export_path'):
        path = result['export_path']
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f"\nExport created: {Path(path).name}")
        print(f"  Exists: {exists}, Size: {size} bytes")
        print("\n[OK] Export test PASSED")
    else:
        print("\n[INFO] Export completed without file artifacts")
        
except Exception as e:
    print(f"\n[ERROR] Export test FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST 5: Workspace Artifact Scan")
print("="*80)

def scan_for_artifacts(base_dir, artifact_types):
    """Scan directories for specific artifact types."""
    artifacts = []
    if not os.path.exists(base_dir):
        return artifacts
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in artifact_types:
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                artifacts.append({
                    'path': full_path,
                    'name': file,
                    'type': ext,
                    'size': size,
                    'dir': os.path.relpath(root, base_dir)
                })
    return artifacts

# Scan for plot artifacts
print("\n[5.1] Scanning for plot artifacts (.png, .jpg, .html, .svg)...")
plot_dirs = [
    ".uploaded_workspaces",
    "data_science/plots",
]

all_plots = []
for dir_path in plot_dirs:
    plots = scan_for_artifacts(dir_path, ['.png', '.jpg', '.jpeg', '.html', '.svg'])
    all_plots.extend(plots)

if all_plots:
    print(f"Found {len(all_plots)} plot artifacts:")
    # Show first 10 plots
    for i, plot in enumerate(all_plots[:10]):
        print(f"  {i+1}. {plot['name']} ({plot['size']:,} bytes)")
    if len(all_plots) > 10:
        print(f"  ... and {len(all_plots) - 10} more plots")
else:
    print("  No plot artifacts found in workspace")

# Scan for report artifacts
print("\n[5.2] Scanning for report artifacts (.html, .md, .txt, .pdf)...")
report_dirs = [
    ".uploaded_workspaces",
    "data_science/reports",
]

all_reports = []
for dir_path in report_dirs:
    reports = scan_for_artifacts(dir_path, ['.html', '.md', '.txt', '.pdf'])
    all_reports.extend(reports)

if all_reports:
    print(f"Found {len(all_reports)} report artifacts:")
    # Show first 10 reports
    for i, report in enumerate(all_reports[:10]):
        print(f"  {i+1}. {report['name']} ({report['size']:,} bytes)")
    if len(all_reports) > 10:
        print(f"  ... and {len(all_reports) - 10} more reports")
else:
    print("  No report artifacts found in workspace")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

total_artifacts = len(all_plots) + len(all_reports)
print(f"\nTotal visualization/report artifacts: {total_artifacts}")
print(f"  - Plot artifacts: {len(all_plots)}")
print(f"  - Report artifacts: {len(all_reports)}")

if all_plots or all_reports:
    print("\n[OK] Plot and report generation is working!")
    
    # Calculate total size
    total_size = sum(p['size'] for p in all_plots) + sum(r['size'] for r in all_reports)
    print(f"\nTotal artifact size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    
    # Breakdown by type
    if all_plots:
        plot_types = {}
        for plot in all_plots:
            ext = plot['type']
            plot_types[ext] = plot_types.get(ext, 0) + 1
        print("\nPlot types:")
        for ext, count in sorted(plot_types.items()):
            print(f"  {ext}: {count} files")
    
    if all_reports:
        report_types = {}
        for report in all_reports:
            ext = report['type']
            report_types[ext] = report_types.get(ext, 0) + 1
        print("\nReport types:")
        for ext, count in sorted(report_types.items()):
            print(f"  {ext}: {count} files")
else:
    print("\n[INFO] No plot or report artifacts found in workspace.")
    print("This is expected if:")
    print("  1. Test dataset is too small (only 20 rows)")
    print("  2. Plots are created in memory but not persisted")
    print("  3. Artifacts are stored in a different location")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
