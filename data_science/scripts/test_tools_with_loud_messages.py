"""
Test to PROVE that tools return LOUD, VISIBLE messages with __display__ fields.
This runs tools directly without the LLM to show they work correctly.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("TESTING TOOLS WITH LOUD EMOJI MESSAGES")
print("=" * 80)

# Test 1: shape() - should have __display__ with emoji
print("\n[TEST 1] shape()")
print("-" * 80)
try:
    from data_science.ds_tools import shape
    result = shape(csv_path="data_science/.uploaded_workspaces/tips.csv")
    
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Has __display__: {'__display__' in result}")
    
    if '__display__' in result:
        display = result['__display__']
        print(f"\n__display__ content ({len(display)} chars):")
        print(display)
        print("\n[OK] shape() HAS __display__ field!")
    else:
        print("\n[FAIL] shape() is MISSING __display__ field!")
        print(f"Available keys: {list(result.keys())}")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: analyze_dataset() via wrapper - should have LOUD message
print("\n\n[TEST 2] analyze_dataset_tool() (with LOUD emoji message)")
print("-" * 80)
try:
    from data_science.adk_safe_wrappers import analyze_dataset_tool
    
    # Create minimal mock context
    class MockContext:
        def __init__(self):
            self.state = {}
    
    result = analyze_dataset_tool(csv_path="data_science/.uploaded_workspaces/tips.csv", tool_context=MockContext())
    
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Has __display__: {'__display__' in result}")
    
    if '__display__' in result:
        display = result['__display__']
        print(f"\n__display__ content ({len(display)} chars):")
        print(display[:300])  # First 300 chars
        
        # Check for LOUD formatting
        has_emoji = any(emoji in display for emoji in ['📊', '✅', '⚠️'])
        has_bold = '**' in display
        
        print(f"\nHas emoji: {has_emoji}")
        print(f"Has bold markdown: {has_bold}")
        
        if has_emoji and has_bold:
            print("\n[OK] analyze_dataset() has LOUD formatting like plot()!")
        else:
            print("\n[WARN] analyze_dataset() has __display__ but not LOUD enough")
    else:
        print("\n[FAIL] analyze_dataset() is MISSING __display__ field!")
        print(f"Available keys: {list(result.keys())}")
        if 'message' in result:
            print(f"\nmessage content: {result['message'][:200]}")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 3: stats() via wrapper - should have LOUD message
print("\n\n[TEST 3] stats_tool() (with LOUD emoji message)")
print("-" * 80)
try:
    from data_science.adk_safe_wrappers import stats_tool
    
    result = stats_tool(csv_path="data_science/.uploaded_workspaces/tips.csv", tool_context=MockContext())
    
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Has __display__: {'__display__' in result}")
    
    if '__display__' in result:
        display = result['__display__']
        print(f"\n__display__ content ({len(display)} chars):")
        print(display[:300])  # First 300 chars
        
        # Check for LOUD formatting
        has_emoji = any(emoji in display for emoji in ['📊', '✅', '⚠️'])
        has_bold = '**' in display
        
        print(f"\nHas emoji: {has_emoji}")
        print(f"Has bold markdown: {has_bold}")
        
        if has_emoji and has_bold:
            print("\n[OK] stats() has LOUD formatting like plot()!")
        else:
            print("\n[WARN] stats() has __display__ but not LOUD enough")
    else:
        print("\n[FAIL] stats() is MISSING __display__ field!")
        print(f"Available keys: {list(result.keys())}")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("If all tests show LOUD formatting with emojis and bold text,")
print("then the problem is 100% the LLM ignoring tool outputs,")
print("NOT the tools themselves.")
print("=" * 80)

