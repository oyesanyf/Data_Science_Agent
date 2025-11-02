"""
Quick test to verify tool outputs have proper display fields.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("TESTING DISPLAY FIELDS IN TOOL OUTPUTS")
print("="*80)

# Test 1: Shape tool
print("\n[TEST 1] shape_tool")
print("-" * 80)
try:
    from data_science.ds_tools import shape
    
    # Find a test file
    test_csv = "simple_test.csv"
    if not Path(test_csv).exists():
        upload_dir = Path(".uploaded")
        if upload_dir.exists():
            csv_files = list(upload_dir.glob("*.csv"))
            if csv_files:
                test_csv = str(csv_files[0])
    
    if Path(test_csv).exists():
        result = shape(csv_path=test_csv)
        
        print(f"Result type: {type(result)}")
        print(f"Has '__display__': {'__display__' in result}")
        print(f"Has 'message': {'message' in result}")
        print(f"Has 'text': {'text' in result}")
        
        if '__display__' in result:
            print(f"\n__display__ content:\n{result['__display__']}")
            print("\n[OK] Shape tool has proper display fields!")
        else:
            print("\n[X] FAIL: Missing __display__ field")
    else:
        print(f"[SKIP] No test file found: {test_csv}")
        
except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: Describe guard
print("\n\n[TEST 2] describe_tool_guard")
print("-" * 80)
try:
    from data_science.head_describe_guard import describe_tool_guard
    
    class MockContext:
        def __init__(self):
            self.state = {}
        def save_artifact(self, *args, **kwargs):
            pass
    
    if Path(test_csv).exists():
        result = describe_tool_guard(tool_context=MockContext(), csv_path=test_csv)
        
        print(f"Result type: {type(result)}")
        print(f"Has '__display__': {'__display__' in result}")
        print(f"Has 'message': {'message' in result}")
        print(f"Has 'text': {'text' in result}")
        
        if '__display__' in result:
            print(f"\n__display__ preview (first 300 chars):\n{result['__display__'][:300]}...")
            print("\n[OK] Describe guard has proper display fields!")
        else:
            print("\n[X] FAIL: Missing __display__ field")
    else:
        print(f"[SKIP] No test file found")
        
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 3: Head guard
print("\n\n[TEST 3] head_tool_guard")
print("-" * 80)
try:
    from data_science.head_describe_guard import head_tool_guard
    
    if Path(test_csv).exists():
        result = head_tool_guard(tool_context=MockContext(), csv_path=test_csv)
        
        print(f"Result type: {type(result)}")
        print(f"Has '__display__': {'__display__' in result}")
        print(f"Has 'message': {'message' in result}")
        print(f"Has 'text': {'text' in result}")
        
        if '__display__' in result:
            print(f"\n__display__ preview (first 300 chars):\n{result['__display__'][:300]}...")
            print("\n[OK] Head guard has proper display fields!")
        else:
            print("\n[X] FAIL: Missing __display__ field")
    else:
        print(f"[SKIP] No test file found")
        
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
print("\nSUMMARY:")
print("- All tools should have '__display__' field as highest priority")
print("- This field contains pre-formatted output for the LLM to display")
print("- LLM is instructed to extract and include this in its response")
print("\nNext: Restart server and test in UI by typing: describe()")

