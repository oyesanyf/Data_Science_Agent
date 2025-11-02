#!/usr/bin/env python3
"""
Test Sequential Workflow Stage Logic
Tests that stages advance correctly and only show one stage at a time
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def test_stage_definitions():
    """Test that all 14 stages are defined correctly"""
    from workflow_stages import WORKFLOW_STAGES, get_stage, get_next_stage
    
    print("=" * 80)
    print("TEST 1: Workflow Stage Definitions")
    print("=" * 80)
    
    print(f"\n1. Total stages defined: {len(WORKFLOW_STAGES)}")
    
    if len(WORKFLOW_STAGES) != 14:
        print(f"   ❌ FAIL: Expected 14 stages, got {len(WORKFLOW_STAGES)}")
        return False
    else:
        print(f"   ✅ PASS: All 14 stages defined")
    
    print(f"\n2. Stage Structure:")
    required_keys = ["id", "name", "icon", "description", "tools", "tip"]
    
    all_valid = True
    for stage in WORKFLOW_STAGES:
        stage_id = stage.get("id", "?")
        missing_keys = [key for key in required_keys if key not in stage]
        
        if missing_keys:
            print(f"   ❌ Stage {stage_id}: Missing keys {missing_keys}")
            all_valid = False
        else:
            tool_count = len(stage.get("tools", []))
            print(f"   ✅ Stage {stage_id}: {stage['name']} ({tool_count} tools)")
    
    if not all_valid:
        print(f"\n   ❌ FAIL: Some stages have missing required keys")
        return False
    
    print(f"\n3. Stage Retrieval:")
    test_ids = [1, 7, 14]
    for stage_id in test_ids:
        stage = get_stage(stage_id)
        print(f"   Stage {stage_id}: {stage['icon']} {stage['name']}")
        if stage['id'] != stage_id:
            print(f"   ❌ FAIL: get_stage({stage_id}) returned wrong stage")
            return False
    print(f"   ✅ PASS: Stage retrieval works")
    
    print(f"\n4. Next Stage Logic:")
    test_cases = [
        (1, 2),   # Stage 1 → Stage 2
        (7, 8),   # Stage 7 → Stage 8
        (13, 14), # Stage 13 → Stage 14
        (14, 14), # Stage 14 → Stage 14 (stays at end)
    ]
    
    for current, expected_next in test_cases:
        next_stage = get_next_stage(current)
        if next_stage['id'] == expected_next:
            print(f"   ✅ Stage {current} → Stage {expected_next}")
        else:
            print(f"   ❌ Stage {current} → Stage {next_stage['id']} (expected {expected_next})")
            return False
    
    print("\n" + "=" * 80)
    print("✅ All stage definition tests PASSED")
    print("=" * 80)
    return True


def test_tool_stage_mapping():
    """Test that tools are correctly mapped to stages"""
    from workflow_stages import get_stage_for_tool
    
    print("\n" + "=" * 80)
    print("TEST 2: Tool-to-Stage Mapping")
    print("=" * 80)
    
    # Test cases: (tool_name, expected_stage)
    test_cases = [
        ("analyze_dataset_tool", 1),
        ("list_data_files_tool", 1),
        ("head_tool_guard", 1),
        ("robust_auto_clean_file_tool", 2),
        ("impute_simple_tool", 2),
        ("encode_categorical_tool", 2),
        ("stats_tool", 3),
        ("correlation_analysis_tool", 3),
        ("plot_tool", 4),
        ("select_features_tool", 5),
        ("train_classifier_tool", 7),
        ("train_regressor_tool", 7),
        ("smart_autogluon_automl", 7),
        ("evaluate_tool", 8),
        ("predict_tool", 9),
        ("export_executive_report_tool", 13),
        ("export_reports_for_latest_run_pathsafe", 14),
    ]
    
    passed = 0
    failed = 0
    
    for tool_name, expected_stage in test_cases:
        stage = get_stage_for_tool(tool_name)
        
        if stage == expected_stage:
            print(f"   ✅ {tool_name} → Stage {stage}")
            passed += 1
        else:
            print(f"   ❌ {tool_name} → Stage {stage} (expected {expected_stage})")
            failed += 1
    
    print(f"\n   Total: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n   ❌ FAIL: Some tools mapped to wrong stages")
        return False
    
    print("\n" + "=" * 80)
    print("✅ All tool mapping tests PASSED")
    print("=" * 80)
    return True


def test_menu_formatting():
    """Test that stage menus are formatted correctly"""
    from workflow_stages import format_stage_menu, get_stage
    
    print("\n" + "=" * 80)
    print("TEST 3: Menu Formatting")
    print("=" * 80)
    
    # Test Stage 1 menu
    stage_1 = get_stage(1)
    menu = format_stage_menu(stage_1)
    
    print(f"\n1. Stage 1 Menu Generated:")
    print(f"   Length: {len(menu)} characters")
    
    # Check required components
    required_elements = [
        ("Stage header", f"WORKFLOW STAGE {stage_1['id']}"),
        ("Stage icon", stage_1['icon']),
        ("Stage name", stage_1['name']),
        ("Description", stage_1['description']),
        ("Tools section", "Available Tools:"),
        ("Tip section", "💡 **TIP:**"),
        ("Progress", f"Stage {stage_1['id']} of 14"),
    ]
    
    all_present = True
    for element_name, element_text in required_elements:
        if element_text in menu:
            print(f"   ✅ Contains: {element_name}")
        else:
            print(f"   ❌ Missing: {element_name}")
            all_present = False
    
    if not all_present:
        print(f"\n   ❌ FAIL: Menu is missing required elements")
        print(f"\n   Generated menu:")
        print(menu)
        return False
    
    # Check that tools are numbered
    tool_count = len(stage_1['tools'])
    print(f"\n2. Tool Listing:")
    print(f"   Expected {tool_count} tools")
    
    numbered_tools = 0
    for i in range(1, tool_count + 1):
        if f"{i}." in menu:
            numbered_tools += 1
    
    if numbered_tools == tool_count:
        print(f"   ✅ All {tool_count} tools are numbered correctly")
    else:
        print(f"   ❌ Only {numbered_tools}/{tool_count} tools are numbered")
        return False
    
    print("\n" + "=" * 80)
    print("✅ All menu formatting tests PASSED")
    print("=" * 80)
    return True


def test_sequential_progression():
    """Test that workflow progresses sequentially"""
    from workflow_stages import get_stage_for_tool, get_next_stage
    
    print("\n" + "=" * 80)
    print("TEST 4: Sequential Workflow Progression")
    print("=" * 80)
    
    # Simulate a typical workflow
    workflow_sequence = [
        ("analyze_dataset_tool", 1, 2),      # Stage 1 tool → advance to Stage 2
        ("robust_auto_clean_file_tool", 2, 3),  # Stage 2 tool → advance to Stage 3
        ("stats_tool", 3, 4),                # Stage 3 tool → advance to Stage 4
        ("plot_tool", 4, 5),                 # Stage 4 tool → advance to Stage 5
        ("select_features_tool", 5, 6),      # Stage 5 tool → advance to Stage 6
        ("train_classifier_tool", 7, 8),     # Stage 7 tool → advance to Stage 8
        ("evaluate_tool", 8, 9),             # Stage 8 tool → advance to Stage 9
    ]
    
    print("\nSimulating workflow progression:")
    current_stage = 1
    
    all_correct = True
    for tool_name, expected_current, expected_next in workflow_sequence:
        tool_stage = get_stage_for_tool(tool_name)
        
        if tool_stage != expected_current:
            print(f"   ❌ {tool_name}: Tool in Stage {tool_stage}, expected Stage {expected_current}")
            all_correct = False
            continue
        
        next_stage = get_next_stage(tool_stage)
        
        if next_stage['id'] == expected_next:
            print(f"   ✅ {tool_name} (Stage {tool_stage}) → Stage {expected_next}")
            current_stage = expected_next
        else:
            print(f"   ❌ {tool_name} (Stage {tool_stage}) → Stage {next_stage['id']} (expected {expected_next})")
            all_correct = False
    
    if not all_correct:
        print("\n   ❌ FAIL: Workflow progression incorrect")
        return False
    
    print("\n" + "=" * 80)
    print("✅ All sequential progression tests PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SEQUENTIAL WORKFLOW STAGE TESTS")
    print("=" * 80)
    
    all_passed = True
    
    # Test 1: Stage definitions
    if not test_stage_definitions():
        all_passed = False
    
    # Test 2: Tool-to-stage mapping
    if not test_tool_stage_mapping():
        all_passed = False
    
    # Test 3: Menu formatting
    if not test_menu_formatting():
        all_passed = False
    
    # Test 4: Sequential progression
    if not test_sequential_progression():
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        print("=" * 80)
        sys.exit(1)

