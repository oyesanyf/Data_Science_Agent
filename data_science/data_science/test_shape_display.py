"""Test script to verify shape tool display output"""
import sys
sys.path.insert(0, "C:\\harfile\\data_science_agent\\data_science")

from adk_safe_wrappers import shape_tool
import json

print("=" * 80)
print("TESTING SHAPE TOOL OUTPUT")
print("=" * 80)

# Call shape_tool without tool_context (simulating independent call)
result = shape_tool()

print("\n[RESULT KEYS]")
print(list(result.keys()))

print("\n[STATUS]")
print(result.get("status"))

print("\n[__DISPLAY__ FIELD]")
display = result.get("__display__")
print(f"Type: {type(display)}")
print(f"Length: {len(str(display)) if display else 0}")
print(f"Content preview: {str(display)[:200] if display else 'NONE'}")

print("\n[MESSAGE FIELD]")
message = result.get("message")
print(f"Type: {type(message)}")
print(f"Length: {len(str(message)) if message else 0}")
print(f"Content preview: {str(message)[:200] if message else 'NONE'}")

print("\n[FULL RESULT (first 500 chars)]")
print(json.dumps({k: str(v)[:100] if not isinstance(v, (int, float, bool, type(None), list)) else v 
                  for k, v in result.items()}, indent=2)[:500])

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

