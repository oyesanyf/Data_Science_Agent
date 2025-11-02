# Contributing to Data Science Agent

First off, thank you for considering contributing to Data Science Agent! It's people like you that make this tool better for everyone.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members
- Be collaborative and constructive

---

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.12 or higher
- `uv` package manager (or `pip`)
- Git
- OpenAI API key
- Basic knowledge of Python and data science

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/data-science-agent.git
   cd data-science-agent
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-owner/data-science-agent.git
   ```

4. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

5. **Install dependencies**:
   ```bash
   uv sync
   # or
   pip install -e ".[dev]"
   ```

6. **Set up environment variables**:
   ```bash
   $env:OPENAI_API_KEY="your-api-key"
   ```

7. **Verify installation**:
   ```bash
   uv run python validate_code.py
   uv run python main.py
   ```

---

## 💻 Development Setup

### Project Structure

```
data_science_agent/
├── data_science/           # Main package
│   ├── agent.py           # Agent configuration
│   ├── ds_tools.py        # Core tools
│   ├── autogluon_tools.py # AutoGluon tools
│   ├── chunk_aware_tools.py
│   └── auto_sklearn_tools.py
├── main.py                # FastAPI server
├── validate_code.py       # Code validator
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml        # Dependencies
```

### Development Tools

We use these tools for development:
- **Code Validation**: `validate_code.py` - Run before committing
- **Linting**: Pylint (optional but recommended)
- **Formatting**: Black or autopep8
- **Type Checking**: mypy (optional)

---

## 🤝 How to Contribute

### Types of Contributions

We welcome many types of contributions:

#### 🐛 Bug Reports
- Use the GitHub Issues page
- Include detailed steps to reproduce
- Provide error messages and logs
- Specify your environment (OS, Python version, etc.)

#### ✨ Feature Requests
- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain why it would be useful
- Consider if it fits the project's scope

#### 📝 Documentation
- Fix typos or clarify existing docs
- Add examples and use cases
- Create tutorials or guides
- Improve code comments

#### 🔧 Code Contributions
- Fix bugs
- Add new tools/features
- Improve performance
- Enhance error handling

---

## 📖 Coding Guidelines

### Python Style Guide

Follow [PEP 8](https://pep8.org/) guidelines:

```python
# Good
def my_function(param: str, tool_context: Optional[ToolContext] = None) -> dict:
    """Function description.
    
    Args:
        param: Parameter description
        tool_context: ADK tool context
    
    Returns:
        dict with results
    """
    result = process_data(param)
    return _json_safe({"result": result})


# Bad
def myFunction(param):  # Wrong naming, no types, no docstring
    return {"result":process_data(param)}  # Inconsistent spacing
```

### Key Principles

1. **Type Hints**: Always use type hints
   ```python
   def my_tool(csv_path: Optional[str] = None, tool_context: Optional[ToolContext] = None) -> dict:
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   """One-line summary.
   
   More detailed description (optional).
   
   Args:
       param_name: Description
       
   Returns:
       Description of return value
       
   Example:
       function_call(param='value')
   """
   ```

3. **Error Handling**: Always handle errors gracefully
   ```python
   try:
       result = operation()
   except SpecificError as e:
       logger.error(f"Operation failed: {e}")
       return {"error": str(e)}
   ```

4. **Async Functions**: Use async for tools
   ```python
   async def my_tool(param: str, tool_context: Optional[ToolContext] = None) -> dict:
       df = await _load_dataframe(csv_path, tool_context=tool_context)
       ...
   ```

5. **JSON Safety**: Always return JSON-safe data
   ```python
   return _json_safe({"result": my_result})
   ```

### Naming Conventions

- **Functions**: `snake_case` (e.g., `train_baseline_model`)
- **Classes**: `PascalCase` (e.g., `DataProcessor`)
- **Constants**: `UPPER_CASE` (e.g., `DATA_DIR`)
- **Private**: Leading underscore (e.g., `_internal_function`)

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ds_tools.py

# Run with coverage
pytest --cov=data_science tests/
```

### Writing Tests

Create test files in the `tests/` directory:

```python
# tests/test_my_tool.py
import pytest
from data_science.ds_tools import my_new_tool

@pytest.mark.asyncio
async def test_my_new_tool():
    """Test my_new_tool with valid input."""
    result = await my_new_tool(param="test_value")
    
    assert result["status"] == "success"
    assert "result" in result

@pytest.mark.asyncio
async def test_my_new_tool_error_handling():
    """Test my_new_tool error handling."""
    result = await my_new_tool(param="invalid")
    
    assert "error" in result
```

### Code Validation

Always run validation before committing:

```bash
uv run python validate_code.py
```

This checks for:
- Syntax errors
- Indentation errors
- Import errors

---

## 📚 Documentation

### Updating Documentation

When adding a new tool, update:

1. **README.md** - Add to tools table
2. **TOOLS_USER_GUIDE.md** - Add comprehensive guide
3. **Docstrings** - In the function itself
4. **QUICK_REFERENCE.md** - Add command example

### Documentation Format

```python
async def my_tool(
    param1: str,
    param2: Optional[int] = None,
    csv_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """One-line description of what the tool does.
    
    Longer description with more details about functionality,
    use cases, and important notes.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: None)
        csv_path: Path to CSV file (default: auto-detect)
        tool_context: ADK tool context (automatically provided)
    
    Returns:
        dict containing:
        - key1: Description
        - key2: Description
        - error: Error message if failed
    
    Example:
        # Basic usage
        my_tool(param1='value')
        
        # With optional parameters
        my_tool(param1='value', param2=10, csv_path='data.csv')
    
    Raises:
        ValueError: If param1 is invalid
        FileNotFoundError: If csv_path doesn't exist
    """
    # Implementation
```

---

## 🔄 Pull Request Process

### Before Submitting

1. ✅ Code follows style guidelines
2. ✅ All tests pass
3. ✅ Code validator passes
4. ✅ Documentation is updated
5. ✅ Commits are clean and descriptive

### Commit Message Format

Use conventional commits:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(tools): add sentiment analysis tool

Implements a new sentiment_analysis() tool that uses
transformers to analyze text sentiment.

Closes #123
```

```
fix(ds_tools): fix logger undefined error

Added missing logger import and initialization to
resolve NameError in explain_model() and export().

Fixes #456
```

### Submitting the PR

1. **Update your fork**:
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```

3. **Make your changes and commit**:
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/my-awesome-feature
   ```

5. **Open a Pull Request** on GitHub

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] All existing tests pass
- [ ] Added new tests
- [ ] Manually tested

## Documentation
- [ ] Updated README.md
- [ ] Updated TOOLS_USER_GUIDE.md
- [ ] Added/updated docstrings
- [ ] Updated CHANGELOG.md

## Screenshots (if applicable)
Add screenshots here

## Related Issues
Closes #issue_number
```

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged
4. Your contribution will be recognized!

---

## 💬 Community

### Getting Help

- **Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Email**: For private concerns
- **Discord**: Join our community (link)

### Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project credits

---

## 🎯 Good First Issues

Look for issues labeled `good-first-issue` for beginner-friendly tasks:
- Documentation improvements
- Adding examples
- Fixing typos
- Small bug fixes

---

## 🔍 Code Review Guidelines

### For Reviewers

- Be constructive and respectful
- Explain why changes are needed
- Suggest alternatives
- Approve when satisfied

### For Contributors

- Address all feedback
- Ask questions if unclear
- Be open to suggestions
- Update based on reviews

---

## 📅 Release Process

We follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Releases are managed by maintainers.

---

## 📝 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You!

Every contribution, no matter how small, makes a difference. Thank you for helping improve Data Science Agent!

---

## 📞 Questions?

If you have questions about contributing:
- Check existing issues and discussions
- Read the documentation
- Open a new discussion
- Contact maintainers

Happy coding! 🚀

