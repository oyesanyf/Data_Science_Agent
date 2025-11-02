"""Test that decorator is properly applied and working."""
import asyncio
from data_science.ds_tools import describe, head, shape
import inspect

print("="*80)
print("TESTING DECORATOR APPLICATION")
print("="*80)

# Test 1: Check if functions are wrapped
print("\n[TEST 1] Checking if functions have decorator...")
for func_name, func in [("describe", describe), ("head", head), ("shape", shape)]:
    # Check if it's wrapped (has __wrapped__ attribute)
    is_wrapped = hasattr(func, '__wrapped__')
    print(f"  {func_name}(): wrapped={is_wrapped}")

# Test 2: Run shape() and check for __display__ field
print("\n[TEST 2] Testing shape() output...")
try:
    # Create a simple test CSV
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df.to_csv('test_decorator.csv', index=False)
    
    # Run shape
    result = shape(csv_path='test_decorator.csv')
    
    print(f"  Result type: {type(result)}")
    print(f"  Has '__display__': {'__display__' in result}")
    print(f"  Has 'message': {'message' in result}")
    
    if '__display__' in result:
        print(f"  __display__ value: {result['__display__'][:100]}")
        print("  [SUCCESS] Decorator is working!")
    else:
        print("  [WARNING] No __display__ field found")
        print(f"  Available fields: {list(result.keys())}")
        
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "="*80)
print("DECORATOR TEST COMPLETE")
print("="*80)

