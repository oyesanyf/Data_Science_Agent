"""
Test script to diagnose describe tool output for UI display.
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the guard wrapper
from data_science.head_describe_guard import describe_tool_guard

# Mock ToolContext
class MockToolContext:
    def __init__(self):
        self.state = {}
    
    def save_artifact(self, *args, **kwargs):
        pass

print("="*80)
print("TESTING DESCRIBE TOOL OUTPUT")
print("="*80)

# Find the test CSV
test_csv = "simple_test.csv"
if not Path(test_csv).exists():
    # Try to find any uploaded CSV
    upload_dir = Path(".uploaded")
    if upload_dir.exists():
        csv_files = list(upload_dir.glob("*.csv"))
        if csv_files:
            test_csv = str(csv_files[0])
            print(f"\nUsing uploaded file: {test_csv}")

if not Path(test_csv).exists():
    print(f"\n[ERROR] Test file not found: {test_csv}")
    print("Please ensure you have a test CSV file.")
    sys.exit(1)

print(f"\nTest CSV: {test_csv}")
print(f"File exists: {Path(test_csv).exists()}")
print(f"File size: {Path(test_csv).stat().st_size if Path(test_csv).exists() else 0} bytes")

# Call the guard
print("\n" + "="*80)
print("CALLING describe_tool_guard...")
print("="*80 + "\n")

tool_context = MockToolContext()
result = describe_tool_guard(tool_context=tool_context, csv_path=test_csv)

print("\n" + "="*80)
print("RESULT FROM describe_tool_guard")
print("="*80)

print(f"\nResult type: {type(result)}")
print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

if isinstance(result, dict):
    print(f"\nStatus: {result.get('status', 'NOT SET')}")
    print(f"Has 'message': {'message' in result}")
    print(f"Has 'ui_text': {'ui_text' in result}")
    print(f"Has 'content': {'content' in result}")
    print(f"Has 'display': {'display' in result}")
    print(f"Has 'overview': {'overview' in result}")
    
    # Print the message field (what should be displayed in UI)
    if 'message' in result:
        print("\n" + "="*80)
        print("MESSAGE FIELD (What should display in UI):")
        print("="*80)
        print(result['message'])
    
    if 'ui_text' in result:
        print("\n" + "="*80)
        print("UI_TEXT FIELD:")
        print("="*80)
        print(result['ui_text'])
    
    # Show a sample of the overview data
    if 'overview' in result:
        print("\n" + "="*80)
        print("OVERVIEW DATA (First 2 columns):")
        print("="*80)
        overview = result['overview']
        if isinstance(overview, dict):
            for i, (col, stats) in enumerate(overview.items()):
                if i >= 2:
                    break
                print(f"\nColumn: {col}")
                print(json.dumps(stats, indent=2))
    
    # Save result to file for inspection
    output_file = "describe_output_diagnostic.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Remove non-serializable items for file output
            serializable_result = {}
            for k, v in result.items():
                try:
                    json.dumps({k: v})
                    serializable_result[k] = v
                except:
                    serializable_result[k] = str(v)[:200]  # Truncate long strings
            json.dump(serializable_result, f, indent=2)
        print(f"\n[OK] Full result saved to: {output_file}")
    except Exception as e:
        print(f"\n[WARNING] Could not save result to file: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

