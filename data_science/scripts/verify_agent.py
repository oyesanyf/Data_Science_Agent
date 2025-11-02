"""
Quick verification script to ensure agent loads with all dependencies.
"""

import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

# Test imports
print("\n--- Testing Imports ---")

try:
    import langchain_text_splitters
    print("[OK] langchain_text_splitters")
except ImportError as e:
    print(f"[FAIL] langchain_text_splitters: {e}")
    sys.exit(1)

try:
    from data_science.chunking_utils import data_chunker, get_safe_csv_reference
    print("[OK] data_science.chunking_utils")
except ImportError as e:
    print(f"[FAIL] data_science.chunking_utils: {e}")
    sys.exit(1)

try:
    from data_science.chunk_aware_tools import smart_autogluon_automl, smart_autogluon_timeseries
    print("[OK] data_science.chunk_aware_tools")
except ImportError as e:
    print(f"[FAIL] data_science.chunk_aware_tools: {e}")
    sys.exit(1)

try:
    from data_science.agent import root_agent
    print("[OK] data_science.agent")
except ImportError as e:
    print(f"[FAIL] data_science.agent: {e}")
    sys.exit(1)

# Verify agent configuration
print(f"\n--- Agent Configuration ---")
print(f"Agent name: {root_agent.name}")
print(f"Model: {root_agent.model}")
print(f"Number of tools: {len(root_agent.tools)}")
print(f"Tools:")
for tool in root_agent.tools:
    tool_name = getattr(tool, 'name', str(tool))
    print(f"  - {tool_name}")

print("\n[SUCCESS] ALL CHECKS PASSED!")
print("\nThe agent is ready to use at http://localhost:8000")

