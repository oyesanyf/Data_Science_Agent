"""
Quick diagnostic to test what the UI should be displaying.
This simulates what happens when a user calls the tools through the agent.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("UI DISPLAY DIAGNOSTIC TEST")
print("="*80)

# Find the most recent uploaded file
test_csv = ".uploaded/1761227823_uploaded.csv"
if not os.path.exists(test_csv):
    # Try to find any CSV
    import glob
    csvs = glob.glob(".uploaded/*.csv")
    if csvs:
        test_csv = max(csvs, key=os.path.getmtime)
        print(f"\nUsing most recent CSV: {test_csv}")
    else:
        print("\n[ERROR] No CSV files found in .uploaded/")
        sys.exit(1)

print(f"\nTest file: {test_csv}")
print(f"File size: {os.path.getsize(test_csv)} bytes")

# Import the guards (what the agent actually calls)
from data_science.head_describe_guard import head_tool_guard, describe_tool_guard
from data_science.adk_safe_wrappers import shape_tool

print("\n" + "="*80)
print("TEST 1: shape_tool() - What the agent calls")
print("="*80)

result = shape_tool(csv_path=test_csv)
print(f"\nReturned keys: {list(result.keys())}")
print(f"Status: {result.get('status')}")

if 'message' in result:
    print(f"\n[message field] (This should display in UI):")
    print(result['message'])
else:
    print("\n[WARNING] No 'message' field in result!")

print("\n" + "="*80)
print("TEST 2: head_tool_guard() - What the agent calls")
print("="*80)

result = head_tool_guard(csv_path=test_csv, n=5)
print(f"\nReturned keys: {list(result.keys())}")
print(f"Status: {result.get('status')}")

if 'message' in result:
    print(f"\n[message field] (This should display in UI):")
    print(result['message'][:500])  # First 500 chars
    print(f"\n...message length: {len(result['message'])} chars")
else:
    print("\n[WARNING] No 'message' field in result!")

if 'head' in result:
    print(f"\nData rows returned: {len(result['head'])}")
    if result['head']:
        print(f"First row: {result['head'][0]}")

print("\n" + "="*80)
print("TEST 3: describe_tool_guard() - What the agent calls")
print("="*80)

result = describe_tool_guard(csv_path=test_csv)
print(f"\nReturned keys: {list(result.keys())}")
print(f"Status: {result.get('status')}")

if 'message' in result:
    print(f"\n[message field] (This should display in UI):")
    print(result['message'][:500])  # First 500 chars
    print(f"\n...message length: {len(result['message'])} chars")
else:
    print("\n[WARNING] No 'message' field in result!")

if 'overview' in result:
    print(f"\nStatistics returned: {len(result['overview'])} columns")

print("\n" + "="*80)
print("TEST 4: Without csv_path (Session State Test)")
print("="*80)

print("\n[4.1] Calling head_tool_guard() without csv_path...")
result = head_tool_guard(n=5)  # No csv_path, no tool_context

print(f"Status: {result.get('status')}")
print(f"Error type: {result.get('error', 'N/A')}")

if 'message' in result:
    print(f"\n[message field]:")
    print(result['message'][:300])
else:
    print("\n[WARNING] No message field!")

print("\n" + "="*80)
print("DIAGNOSIS SUMMARY")
print("="*80)

print("\n✅ If you see formatted 'message' fields above with tables and statistics,")
print("   the guards are working correctly!")
print("\n⚠️  If you see 'No message field' warnings, there's a formatting issue.")
print("\n💡 The agent should be displaying these 'message' fields in the chat UI.")
print("   If the user isn't seeing them, the agent might not be including")
print("   tool results in its response.")

print("\n📝 RECOMMENDATION:")
print("   In the UI, try asking explicitly:")
print("   - 'Show me the head() output'")
print("   - 'What did shape() return?'")
print("   - 'Display the describe() statistics'")
print("\n   This forces the agent to include the tool results in its response.")

print("\n" + "="*80)

