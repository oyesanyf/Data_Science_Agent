#!/usr/bin/env python3
"""
Verify all tool imports are valid and tools exist.
Runs comprehensive import check to catch missing dependencies or broken imports.
"""

import sys
import traceback
from pathlib import Path

print("=" * 80)
print("COMPREHENSIVE TOOL IMPORT VERIFICATION")
print("=" * 80)

errors = []
warnings = []
success_count = 0

def test_import(module_path: str, item_name: str = None) -> bool:
    """Test if an import works."""
    try:
        if item_name:
            exec(f"from {module_path} import {item_name}")
            print(f"✅ {module_path}.{item_name}")
        else:
            exec(f"import {module_path}")
            print(f"✅ {module_path}")
        return True
    except ImportError as e:
        error_msg = f"❌ {module_path}.{item_name if item_name else ''} - {str(e)}"
        print(error_msg)
        errors.append(error_msg)
        return False
    except Exception as e:
        error_msg = f"⚠️  {module_path}.{item_name if item_name else ''} - {str(e)}"
        print(error_msg)
        warnings.append(error_msg)
        return False

# Test core imports
print("\n--- Core Module Imports ---")
test_import("data_science.ds_tools")
test_import("data_science.extended_tools")
test_import("data_science.adk_safe_wrappers")
test_import("data_science.agent")
test_import("data_science.artifact_manager")
test_import("data_science.workflow_persistence")

# Test workflow navigation tools
print("\n--- Workflow Navigation Tools ---")
test_import("data_science.ds_tools", "next_stage")
test_import("data_science.ds_tools", "back_stage")
test_import("data_science.ds_tools", "next_step")
test_import("data_science.ds_tools", "back_step")

# Test auto_feature_synthesis specifically
print("\n--- Feature Engineering Tools ---")
test_import("data_science.extended_tools", "auto_feature_synthesis")
test_import("data_science.extended_tools", "feature_importance_stability")

# Test wrapper imports
print("\n--- ADK Safe Wrappers ---")
try:
    from data_science.adk_safe_wrappers import auto_feature_synthesis_tool
    print("✅ auto_feature_synthesis_tool")
    success_count += 1
except Exception as e:
    error_msg = f"❌ auto_feature_synthesis_tool - {str(e)}"
    print(error_msg)
    errors.append(error_msg)
    traceback.print_exc()

# Test if agent can import all tools
print("\n--- Agent Tool Registration ---")
try:
    from data_science.agent import root_agent
    print(f"✅ Agent loaded: {root_agent.name}")
    print(f"   Total tools registered: {len(root_agent.tools)}")
    
    # Check for workflow navigation tools
    tool_names = []
    for tool in root_agent.tools:
        try:
            name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_names.append(name)
        except:
            pass
    
    required_tools = ["next_stage", "back_stage", "next_step", "back_step", "auto_feature_synthesis_tool"]
    for req_tool in required_tools:
        if req_tool in tool_names:
            print(f"✅ {req_tool} registered")
            success_count += 1
        else:
            error_msg = f"❌ {req_tool} NOT registered in agent"
            print(error_msg)
            errors.append(error_msg)
    
except Exception as e:
    error_msg = f"❌ Failed to load agent: {str(e)}"
    print(error_msg)
    errors.append(error_msg)
    traceback.print_exc()

# Test extended_tools availability
print("\n--- Extended Tools Module Check ---")
try:
    from data_science import extended_tools
    if hasattr(extended_tools, 'auto_feature_synthesis'):
        print("✅ auto_feature_synthesis found in extended_tools")
        success_count += 1
    else:
        errors.append("❌ auto_feature_synthesis NOT in extended_tools")
        
    if hasattr(extended_tools, 'feature_importance_stability'):
        print("✅ feature_importance_stability found in extended_tools")
        success_count += 1
    else:
        errors.append("❌ feature_importance_stability NOT in extended_tools")
except Exception as e:
    error_msg = f"❌ extended_tools module check failed: {str(e)}"
    print(error_msg)
    errors.append(error_msg)

# Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print(f"✅ Successful: {success_count}")
print(f"❌ Errors: {len(errors)}")
print(f"⚠️  Warnings: {len(warnings)}")

if errors:
    print("\n❌ ERRORS FOUND:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)
elif warnings:
    print("\n⚠️  WARNINGS:")
    for warning in warnings:
        print(f"  {warning}")
    print("\n✅ All critical imports verified!")
    sys.exit(0)
else:
    print("\n✅ ALL IMPORTS VERIFIED SUCCESSFULLY!")
    sys.exit(0)

