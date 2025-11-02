"""
Test script to verify analyze_dataset_tool and other tools are properly fixed.
"""
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all tools can be imported."""
    try:
        from data_science.adk_safe_wrappers import (
            analyze_dataset_tool,
            describe_tool,
            shape_tool,
            stats_tool,
            correlation_analysis_tool,
            _ensure_ui_display,
            _log_tool_result_diagnostics
        )
        logger.info("✅ All tools imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_analyze_dataset_returns_display():
    """Test that analyze_dataset_tool calls _ensure_ui_display."""
    import inspect
    from data_science.adk_safe_wrappers import analyze_dataset_tool
    
    # Get source code
    source = inspect.getsource(analyze_dataset_tool)
    
    # Check for our fixes
    has_log_diagnostics = "_log_tool_result_diagnostics" in source
    has_ensure_display = "return _ensure_ui_display" in source
    has_no_skip_comment = "DON'T call _ensure_ui_display" not in source
    
    logger.info(f"analyze_dataset_tool checks:")
    logger.info(f"  - Has _log_tool_result_diagnostics: {'✅' if has_log_diagnostics else '❌'}")
    logger.info(f"  - Has return _ensure_ui_display: {'✅' if has_ensure_display else '❌'}")
    logger.info(f"  - Removed skip comment: {'✅' if has_no_skip_comment else '❌'}")
    
    return has_log_diagnostics and has_ensure_display and has_no_skip_comment

def test_correlation_analysis_exists():
    """Test that correlation_analysis_tool exists and is registered."""
    try:
        from data_science.adk_safe_wrappers import correlation_analysis_tool
        from data_science import agent
        
        # Check if registered in agent
        tool_names = [str(t) for t in agent.root_agent.tools]
        has_correlation = any("correlation" in str(t).lower() for t in tool_names)
        
        logger.info(f"correlation_analysis_tool:")
        logger.info(f"  - Exists: ✅")
        logger.info(f"  - Registered in agent: {'✅' if has_correlation else '❌'}")
        logger.info(f"  - Total agent tools: {len(agent.root_agent.tools)}")
        
        return has_correlation
    except Exception as e:
        logger.error(f"❌ correlation_analysis_tool test failed: {e}")
        return False

def test_agent_log_configured():
    """Test that agent.log is properly configured."""
    from pathlib import Path
    from data_science.logging_config import CONSOLE_LOG
    
    expected = Path("agent.log")  # Should be singular, not plural
    actual = CONSOLE_LOG.name
    
    correct = actual == "agent.log"
    logger.info(f"agent.log configuration:")
    logger.info(f"  - File name: {actual} ({'✅' if correct else '❌'})")
    logger.info(f"  - Full path: {CONSOLE_LOG}")
    
    return correct

def main():
    """Run all tests."""
    logger.info("=" * 70)
    logger.info("Testing Data Science Agent Fixes")
    logger.info("=" * 70)
    
    results = {
        "Imports": test_imports(),
        "analyze_dataset_tool fix": test_analyze_dataset_returns_display(),
        "correlation_analysis_tool": test_correlation_analysis_exists(),
        "agent.log config": test_agent_log_configured(),
    }
    
    logger.info("\n" + "=" * 70)
    logger.info("Test Results Summary")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name:30s} {status}")
    
    all_passed = all(results.values())
    
    logger.info("=" * 70)
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED - Fixes are working!")
        logger.info("\nNext steps:")
        logger.info("1. Restart the agent: python main.py")
        logger.info("2. Upload a CSV file")
        logger.info("3. Run: analyze_dataset()")
        logger.info("4. You should see actual data, not just 'success'")
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED - Please check the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())

