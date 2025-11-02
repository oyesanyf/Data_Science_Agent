# Project Organization

This document describes the file organization structure of the Data Science Agent project.

## Root Directory

The root directory contains only essential files needed for a Git repository and project setup:

### Core Project Files
- **`README.md`** - Project overview and quick start
- **`LICENSE`** - MIT License
- **`CONTRIBUTING.md`** - Contribution guidelines
- **`CODE_OF_CONDUCT.md`** - Community guidelines
- **`SECURITY.md`** - Security policy and reporting
- **`.gitignore`** - Git ignore patterns

### Configuration Files
- **`pyproject.toml`** - Python project configuration (PEP 518)
- **`requirements.txt`** - Python dependencies
- **`requirements-gpu.txt`** - GPU-specific dependencies
- **`requirements-linux.txt`** - Linux-specific dependencies
- **`env.template`** - Environment variable template
- **`Dockerfile`** - Docker container configuration
- **`uv.lock`** - UV package manager lock file

### Entry Points & Server Scripts
- **`main.py`** - Main application entry point
- **`start_server.py`** - Server startup script (Python)
- **`start_server.ps1`** - Server startup script (PowerShell/Windows)
- **`start_server.bat`** - Server startup script (Batch/Windows)
- **`restart_server.ps1`** - Server restart script

### Visual Assets
- **`data-science-architecture.png`** - Architecture diagram

## Directory Structure

```
data_science_agent/
├── README.md                   # Main project documentation
├── LICENSE                     # MIT License
├── CONTRIBUTING.md             # How to contribute
├── CODE_OF_CONDUCT.md          # Community standards
├── SECURITY.md                 # Security reporting
├── .gitignore                  # Git ignore rules
│
├── pyproject.toml              # Project config
├── requirements*.txt           # Dependencies
├── env.template                # Environment template
├── Dockerfile                  # Docker config
│
├── main.py                     # App entry point
├── start_server.*              # Startup scripts
├── restart_server.ps1          # Restart script
│
├── data_science/               # Main package
│   ├── __init__.py
│   ├── agent.py                # Agent definition
│   ├── ds_tools.py             # 150+ ML tools
│   ├── adk_safe_wrappers.py   # Tool wrappers
│   ├── streaming_all.py        # Streaming tools
│   ├── callbacks.py            # Agent callbacks
│   ├── artifact_manager.py     # Artifact handling
│   │
│   ├── utils/                  # Utility modules
│   │   ├── io.py               # I/O utilities
│   │   ├── paths.py            # Path handling
│   │   └── ...
│   │
│   ├── docs/                   # Documentation (200+ files)
│   │   ├── README.md           # Documentation index
│   │   ├── ARCHITECTURE.md     # Architecture docs
│   │   ├── *.md                # All other documentation
│   │   └── ...
│   │
│   └── scripts/                # Development scripts
│       ├── README.md           # Scripts documentation
│       ├── test_*.py           # Test scripts
│       ├── verify_*.py         # Verification scripts
│       ├── check_*.py          # Check scripts
│       ├── apply_*.py          # Utility scripts
│       └── *.ps1/*.bat/*.sh    # Shell scripts
│
└── uploads/                    # User uploads (gitignored)
    └── _workspaces/            # Workspace data (gitignored)
```

## File Organization Principles

### What Stays in Root
✅ Essential project files (README, LICENSE, etc.)
✅ Configuration files (requirements, pyproject.toml)
✅ Entry points (main.py, start_server.*)
✅ Docker configuration
✅ Environment templates

### What Goes in `data_science/`
✅ All Python source code
✅ Core modules and tools
✅ Utility modules
✅ Agent definitions

### What Goes in `data_science/docs/`
✅ All markdown documentation (except root essentials)
✅ Architecture documents
✅ User guides
✅ API references
✅ Implementation notes
✅ Fix/changelog documentation

### What Goes in `data_science/scripts/`
✅ Development and testing scripts
✅ Verification utilities
✅ Code generation tools
✅ Utility shell scripts
✅ Maintenance scripts

### What Gets Gitignored
❌ User data (uploads/, _workspaces/)
❌ Generated files (*.pyc, __pycache__/)
❌ Model files (*.pkl, *.joblib)
❌ Log files (*.log, logs/)
❌ Test data files (test_*.csv)
❌ Environment files (.env)
❌ Build artifacts (dist/, build/)

## Why This Organization?

### Clean Root Directory
- Makes the repository easier to navigate
- Follows Git repository best practices
- Essential files are immediately visible
- Reduces cognitive load for new contributors

### Centralized Documentation
- All docs in one place (`data_science/docs/`)
- Easy to find and maintain
- Clear separation from code
- Better for documentation generation

### Separated Concerns
- **Source code**: `data_science/`
- **Documentation**: `data_science/docs/`
- **Utilities**: `data_science/scripts/`
- **User data**: `uploads/` (gitignored)

### Benefits
1. ✅ **Clarity**: Clear purpose for each directory
2. ✅ **Maintainability**: Easy to find and update files
3. ✅ **Scalability**: Structure supports growth
4. ✅ **Standards**: Follows Python/Git best practices
5. ✅ **Navigation**: Logical organization aids discovery

## Finding Documentation

### Quick Access
- **Start here**: `README.md` in root
- **Full docs**: `data_science/docs/README.md`
- **API docs**: `data_science/docs/COMPLETE_API_REFERENCE.md`
- **Quick start**: `data_science/docs/QUICK_START.md`

### By Topic
All documentation is indexed in `data_science/docs/README.md` with categories:
- Quick Start & Installation
- Core Documentation
- Tool-Specific Guides
- Advanced Topics
- Recent Updates & Fixes
- Troubleshooting
- Reference Documentation

## Maintenance

### Adding New Files

**New documentation?** → Add to `data_science/docs/` and update index

**New utility script?** → Add to `data_science/scripts/` with README entry

**New source file?** → Add to appropriate `data_science/` subdirectory

**New test?** → Add to `data_science/scripts/` with `test_` prefix

### Cleaning Up

Run maintenance to clean old data files:
```python
from data_science.ds_tools import maintenance

# Safe cleanup of old data files only
maintenance(action="clean_data")
maintenance(action="clean_logs")
maintenance(action="clean_temp")
```

See [`data_science/docs/MAINTENANCE_SAFETY_FIX.md`](data_science/docs/MAINTENANCE_SAFETY_FIX.md) for details.

## Migration Notes

All documentation files (`*.md` except root essentials) have been moved from the root to `data_science/docs/`.

If you have bookmarks or references to old documentation paths:
- Old: `ARCHITECTURE.md`
- New: `data_science/docs/ARCHITECTURE.md`

---

**Last Updated**: October 2025

