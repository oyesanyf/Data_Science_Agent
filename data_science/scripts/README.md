# Utility Scripts

This directory contains utility scripts for development, testing, and maintenance.

## Testing Scripts

### Unit Tests
- `test_all_data_tools.py` - Test all data science tools
- `test_artifacts.py` - Test artifact handling
- `test_chunking.py` - Test data chunking
- `test_decorator_works.py` - Test decorator functionality
- `test_describe_output.py` - Test describe tool output
- `test_display_fields.py` - Test UI display fields
- `test_memory_leak_fix.py` - Memory leak tests
- `test_model_folder_names.py` - Model folder naming tests
- `test_model_organization.py` - Model organization tests
- `test_openai_simple.py` - OpenAI integration tests
- `test_plots_reports.py` - Plot and report tests
- `test_tools_with_loud_messages.py` - Tool output tests
- `test_ui_display.py` - UI display tests
- `test_debug_code.py` - Debug utilities test

## Verification Scripts

- `verify_agent.py` - Verify agent functionality
- `verify_agent_tools.py` - Verify all tools work
- `verify_all_decorators.py` - Check decorators applied
- `verify_all_tools.py` - Comprehensive tool verification
- `verify_production.py` - Production readiness check
- `verify_server_code.py` - Server code validation
- `validate_code.py` - Code validation

## Development Utilities

- `check_imports.py` - Check import statements
- `check_ui_sink.py` - Verify UI sink functionality
- `apply_display_fix_all_tools.py` - Apply UI display fixes
- `apply_display_to_all_tools.py` - Batch apply display fixes
- `auto_add_decorator.py` - Auto-add decorators
- `add_decorator_to_all_tool_files.py` - Batch decorator addition
- `remove_df_type_annotations.py` - Remove DataFrame type hints

## Usage

### Running Tests

```bash
# Run all tool tests
python scripts/test_all_data_tools.py

# Verify production readiness
python scripts/verify_production.py

# Check imports
python scripts/check_imports.py
```

### Running Utilities

```bash
# Validate code
python scripts/validate_code.py

# Verify agent
python scripts/verify_agent.py

# Check UI sink
python scripts/check_ui_sink.py
```

## Notes

- All test scripts assume they're run from the project root
- Some scripts may require specific environment variables set
- Check individual script docstrings for specific usage

---

**Warning**: These are development/testing scripts. Do not use in production unless you understand what they do.

