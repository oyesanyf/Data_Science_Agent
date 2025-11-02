# 🍎 macOS Folder Configuration Guide

## ✅ Fully Configurable Folder Structure

The Data Science Agent now supports **fully configurable folder paths** via `.env` file, with **macOS-specific recommendations**!

---

## 🎯 Quick Setup for macOS

### Option 1: Mac-Friendly Location (Recommended)

```bash
# 1. Copy env template
cp env.template .env

# 2. Edit .env and uncomment macOS path:
nano .env  # or use your preferred editor
```

**Uncomment this line in `.env`:**
```bash
# macOS RECOMMENDED PATH
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent
```

**Result - Same structure as Windows, just in Mac-friendly location:**
```
~/Documents/DataScienceAgent/
└── .uploaded/
    └── _workspaces/
        └── <dataset_name>/<timestamp>/
            ├── uploads/        # Uploaded CSV files
            ├── data/           # Processed data
            ├── models/         # Trained models
            ├── reports/        # Generated reports
            ├── plots/          # Visualizations
            ├── metrics/        # Evaluation metrics
            ├── indexes/        # Vector indexes
            ├── logs/           # Tool logs
            ├── tmp/            # Temporary files
            ├── manifests/      # Metadata
            └── unstructured/   # Unstructured data
```

---

### Option 2: Use Default (Windows-style)

Leave paths as default:
```bash
AGENT_UPLOAD_DIR=.uploaded
```

**Result:**
```
<project_directory>/
└── .uploaded/
    ├── _workspaces/
    │   └── <dataset_name>/<timestamp>/
    └── ...
```

---

## 📋 Configurable Paths

| Environment Variable | Default | macOS Recommended | Description |
|---------------------|---------|-------------------|-------------|
| `AGENT_UPLOAD_DIR` | `.uploaded` | `~/Documents/DataScienceAgent` | Root directory - creates `.uploaded/_workspaces/` inside |
| `DUCKDB_TEMP_DIR` | `/tmp/duckdb_spill` | `~/Library/Caches/DataScienceAgent/duckdb` | DuckDB temp files for large datasets |

**Advanced (rarely needed):**
| `AGENT_WORKSPACES_DIR` | `{UPLOAD_DIR}/_workspaces` | - | Override workspace location |
| `AGENT_MODELS_DIR` | `{workspace}/models` | `/Volumes/ExternalDrive/models` | Store models on external drive |
| `AGENT_REPORTS_DIR` | `{workspace}/reports` | `~/Dropbox/Reports` | Sync reports to cloud |
| `AGENT_PLOTS_DIR` | `{workspace}/plots` | - | Custom plots location |

---

## 🔧 Path Features

### 1. Tilde (`~`) Expansion
All paths support `~` which expands to your home directory:
```bash
# These are equivalent on macOS:
AGENT_UPLOAD_DIR=~/Documents/Data
AGENT_UPLOAD_DIR=/Users/yourname/Documents/Data
```

### 2. Relative Paths
Use relative paths from project root:
```bash
AGENT_UPLOAD_DIR=./data/uploads
AGENT_WORKSPACES_DIR=./data/workspaces
```

### 3. Absolute Paths
Use full paths for any location:
```bash
AGENT_UPLOAD_DIR=/Volumes/ExternalDrive/DataScience/uploads
AGENT_MODELS_DIR=/Volumes/ExternalDrive/DataScience/models
```

### 4. Custom per Directory
Mix and match as needed:
```bash
# Uploads on local disk
AGENT_UPLOAD_DIR=~/Documents/DataScience/uploads

# Models on external drive (more space)
AGENT_MODELS_DIR=/Volumes/ExternalDrive/models

# Reports in Dropbox (auto-sync)
AGENT_REPORTS_DIR=~/Dropbox/DataScienceReports
```

---

## 🍎 macOS-Specific Recommendations

### 1. Standard Location (Recommended)

**Single root directory** - maintains Windows workspace structure:
```bash
# Everything under Documents/DataScienceAgent (user-visible)
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent

# This creates:
# ~/Documents/DataScienceAgent/.uploaded/_workspaces/<dataset>/<timestamp>/
#   ├── uploads/
#   ├── data/
#   ├── models/
#   ├── reports/
#   ├── plots/
#   └── ...
```

**Optional temp directory:**
```bash
# For DuckDB temporary files (large datasets)
DUCKDB_TEMP_DIR=~/Library/Caches/DataScienceAgent/duckdb
```

### 2. External Drives (for Large Datasets)

Store everything on external drive:
```bash
AGENT_UPLOAD_DIR=/Volumes/MyDrive/DataScienceAgent
# Creates: /Volumes/MyDrive/DataScienceAgent/.uploaded/_workspaces/...
```

### 3. Network Storage (NAS)

Store on network drive:
```bash
AGENT_UPLOAD_DIR=/Volumes/NAS/DataScienceAgent
# Creates: /Volumes/NAS/DataScienceAgent/.uploaded/_workspaces/...
```

### 4. Advanced: Split Locations (Rarely Needed)

**Only if you need different files in different places:**

```bash
# Data on local SSD
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent

# Models on external drive (more space)
AGENT_MODELS_DIR=/Volumes/ExternalDrive/models

# Reports in iCloud (sync across devices)
AGENT_REPORTS_DIR=~/Library/Mobile Documents/com~apple~CloudDocs/Reports
```

**⚠️ Note:** This breaks the unified workspace structure. Not recommended unless you have specific needs.

---

## 🚀 Complete macOS Setup Example

```bash
#!/bin/bash
# setup_macos.sh - Complete macOS setup

# 1. Clone repository
git clone <your-repo-url>
cd data-science-agent

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# 3. Create .env from template
cp env.template .env

# 4. Configure macOS path (keeps same workspace structure as Windows)
cat >> .env << 'EOF'

# macOS Configuration - stores everything in ~/Documents/DataScienceAgent
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent

# Optional: DuckDB temp directory
# DUCKDB_TEMP_DIR=~/Library/Caches/DataScienceAgent/duckdb

# Your API keys
OPENAI_API_KEY=sk-your-key-here
EOF

# 5. Install dependencies
uv sync

# 6. Run configuration test
uv run python -c "from data_science.large_data_config import print_config; print_config()"

# 7. Start server
uv run python main.py
```

**Save as `setup_macos.sh` and run:**
```bash
chmod +x setup_macos.sh
./setup_macos.sh
```

---

## 🔍 Verify Configuration

Check your folder configuration:
```bash
# Run config printer
python -c "from data_science.large_data_config import print_config; print_config()"
```

**Expected Output:**
```
======================================================================
LARGE DATASET CONFIGURATION
======================================================================

Folder Structure:
  Upload Root: /Users/yourname/Documents/DataScienceAgent/.uploaded
  Workspaces Root: /Users/yourname/Documents/DataScienceAgent/.uploaded/_workspaces
  DuckDB Temp: /tmp/duckdb_spill

Data Processing:
  Upload Chunk Size: 4 MB
  Parquet Row Group: 256 MB
  Profile Sample: 500,000 rows
  ...

Model Training:
  AutoML Time Limit: 1800s
  ...
======================================================================
```

**Workspace Structure Created:**
```
/Users/yourname/Documents/DataScienceAgent/
└── .uploaded/
    └── _workspaces/
        └── <dataset_name>/<timestamp>/
            ├── uploads/
            ├── data/
            ├── models/
            ├── reports/
            ├── plots/
            └── ...
```

---

## 💡 Pro Tips

### 1. Symlink for Easy Access
Create alias in Finder sidebar:
```bash
# Make it easy to find
ln -s ~/Documents/DataScienceAgent ~/Desktop/DataScienceAgent
```

### 2. Backup Configuration
```bash
# Backup important folders
cp .env .env.backup

# Use Time Machine
# macOS automatically backs up ~/Documents
```

### 3. Permissions
Ensure proper permissions:
```bash
# Fix permissions if needed
chmod 755 ~/Documents/DataScienceAgent
chmod 644 ~/Documents/DataScienceAgent/.env
```

### 4. Spotlight Integration
macOS Spotlight will index your reports and plots automatically if they're in `~/Documents/`.

### 5. Quick Look Support
PDF reports and PNG plots support Quick Look (spacebar in Finder).

---

## 🔧 Troubleshooting

### Issue: "Permission denied"

**Solution:**
```bash
# Check permissions
ls -la ~/Documents/DataScienceAgent

# Fix if needed
chmod -R u+rw ~/Documents/DataScienceAgent
```

### Issue: "No such file or directory"

**Solution:**
```bash
# Create directories manually
mkdir -p ~/Documents/DataScienceAgent/{uploads,workspaces,models,reports,plots}
mkdir -p ~/Library/Caches/DataScienceAgent/duckdb
```

### Issue: External drive not found

**Solution:**
```bash
# Check mounted volumes
ls -l /Volumes/

# Mount drive if needed
# (usually automatic on macOS)
```

### Issue: iCloud Drive slow

**Solution:**
```bash
# Don't use iCloud for large datasets
# Use for reports only:
AGENT_REPORTS_DIR=~/Library/Mobile Documents/com~apple~CloudDocs/Reports
# Keep data local:
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent/uploads
```

---

## 📊 Comparison: Windows vs macOS vs Linux

| Aspect | Windows | macOS | Linux |
|--------|---------|-------|-------|
| **Default** | `.uploaded/` | `.uploaded/` | `.uploaded/` |
| **Recommended** | `.uploaded/` | `~/Documents/DataScienceAgent/` | `~/.local/share/data-science-agent/` |
| **Path Style** | Backslash `\` | Forward slash `/` | Forward slash `/` |
| **Tilde** | Not supported | ✅ Supported | ✅ Supported |
| **Hidden Files** | Attribute-based | Dot-prefix `.` | Dot-prefix `.` |
| **Case Sensitive** | No | No (by default) | Yes |

---

## ✅ Summary

**Key Points:**
- ✅ **Same workspace structure as Windows** - `.uploaded/_workspaces/<dataset>/<timestamp>/`
- ✅ **Single path to configure** - Just set `AGENT_UPLOAD_DIR`
- ✅ **Supports `~` expansion** - Use `~/Documents/DataScienceAgent`
- ✅ **Works everywhere** - Relative paths, absolute paths, network drives, external drives
- ✅ **Auto-creates directories** - No manual setup needed

**macOS Recommendation:**
```bash
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent
```

**This creates:**
```
~/Documents/DataScienceAgent/
└── .uploaded/
    └── _workspaces/
        └── <dataset>/<timestamp>/
            ├── uploads/
            ├── data/
            ├── models/
            ├── reports/
            ├── plots/
            └── ...
```

**Getting Started:**
1. Copy `env.template` to `.env`
2. Uncomment `AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent`
3. Add your `OPENAI_API_KEY`
4. Run `uv run python main.py`
5. Everything works! ✨

---

**Last Updated:** October 24, 2025  
**Platform:** macOS 11+ (Big Sur and later)  
**Compatibility:** Also works on Linux, Windows

