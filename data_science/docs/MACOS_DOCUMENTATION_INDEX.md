# 🍎 macOS Documentation Index

Complete guide to all macOS-related documentation for the Data Science Agent.

---

## 📚 Main macOS Documentation

### 1. **macOS Folder Configuration** ⭐ NEW!
**File:** [`MACOS_FOLDER_CONFIGURATION.md`](./MACOS_FOLDER_CONFIGURATION.md)

**What it covers:**
- ✅ Configurable folder paths via `.env` file
- ✅ macOS-specific path recommendations
- ✅ Same workspace structure as Windows
- ✅ Tilde (`~`) expansion support
- ✅ External drive and NAS configuration
- ✅ Complete setup examples
- ✅ Troubleshooting guide

**Quick Setup:**
```bash
# 1. Copy template
cp env.template .env

# 2. Edit .env and add:
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent
OPENAI_API_KEY=sk-your-key-here

# 3. Run
python main.py
```

---

### 2. **Installation Guide**
**File:** [`INSTALLATION.md`](./INSTALLATION.md)

**macOS sections:**
- Prerequisites for macOS
- Installing uv on macOS
- Python 3.12+ installation with Homebrew
- macOS-specific setup steps
- macOS troubleshooting

**Quick Install (macOS):**
```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.12

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd data-science-agent
uv sync

# Start
uv run python main.py
```

---

### 3. **Installation Guide (Detailed)**
**File:** [`INSTALLATION_GUIDE.md`](./INSTALLATION_GUIDE.md)

**Covers:**
- Step-by-step macOS installation
- UV package manager setup
- Environment configuration
- Verification steps
- macOS-specific notes

---

## 🍏 Platform-Specific Features

### 4. **Windows Compatibility**
**File:** [`WINDOWS_COMPATIBILITY.md`](./WINDOWS_COMPATIBILITY.md)

**Why macOS users care:**
- Explains which packages work on macOS vs Windows
- `auto-sklearn` works on macOS but NOT on Windows
- Cross-platform considerations

**Key Point:**
```bash
# macOS/Linux can use real auto-sklearn:
pip install -r requirements.txt
pip install -r requirements-linux.txt

# Windows cannot (but works fine without it)
```

---

### 5. **GPU Support**
**File:** [`GPU_ACCELERATION_GUIDE.md`](./GPU_ACCELERATION_GUIDE.md) and [`GPU_SUPPORT_ADDED.md`](./GPU_SUPPORT_ADDED.md)

**macOS GPU Support:**
- ✅ **Apple Silicon (M1/M2/M3):** Uses MPS (Metal Performance Shaders)
- ✅ **Intel Mac with eGPU:** Can use NVIDIA CUDA
- ✅ **Automatic detection:** PyTorch detects MPS/CUDA automatically
- ✅ **Fallback to CPU:** If no GPU available

**Check MPS on Apple Silicon:**
```bash
python -c "import torch; print(f'MPS Available: {torch.backends.mps.is_available()}')"
```

---

## 📁 Folder Structure & Paths

### 6. **Folder Structure Explained**
**File:** [`FOLDER_STRUCTURE_EXPLAINED.md`](./FOLDER_STRUCTURE_EXPLAINED.md)

**Workspace structure (same on all platforms):**
```
<root>/.uploaded/_workspaces/<dataset>/<timestamp>/
  ├── uploads/        # Uploaded CSV files
  ├── data/           # Processed/cleaned data
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

**macOS default location:**
```
~/Documents/DataScienceAgent/.uploaded/_workspaces/...
```

---

## 🚀 Quick Start Guides

### 7. **Quick Start**
**File:** [`QUICK_START.md`](./QUICK_START.md)

Platform-agnostic quick start with macOS examples.

### 8. **Quick Start for Large Datasets**
**File:** [`QUICK_START_LARGE_DATASETS.md`](./QUICK_START_LARGE_DATASETS.md)

Optimizations for macOS with large datasets:
- Polars streaming mode
- DuckDB configuration
- Memory management
- External drive usage

---

## 🔧 Configuration & Setup

### 9. **Environment Variables**
**File:** `env.template` (root directory)

**macOS-specific variables:**
```bash
# macOS Recommended Path
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent

# Optional: Custom temp directory
DUCKDB_TEMP_DIR=~/Library/Caches/DataScienceAgent/duckdb

# API Keys
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-key-here  # For ensemble mode
```

### 10. **Startup Scripts**
**Files:** [`STARTUP_SCRIPTS_UPDATED.md`](./STARTUP_SCRIPTS_UPDATED.md), [`ALL_STARTUP_SCRIPTS_UPDATED.md`](./ALL_STARTUP_SCRIPTS_UPDATED.md)

**macOS startup:**
```bash
# Option 1: Python script
python start_server.py

# Option 2: UV
uv run python main.py

# Option 3: Direct
python main.py
```

---

## 📦 Package Installation

### 11. **Install Requirements**
**File:** [`INSTALL_REQUIREMENTS.md`](./INSTALL_REQUIREMENTS.md)

**macOS installation methods:**
```bash
# Method 1: UV (fastest)
uv sync

# Method 2: pip
pip install -r requirements.txt

# Method 3: With auto-sklearn (macOS only)
pip install -r requirements.txt
pip install -r requirements-linux.txt
```

### 12. **Auto-Install Guide**
**File:** [`AUTO_INSTALL_GUIDE.md`](./AUTO_INSTALL_GUIDE.md)

Automatic dependency installation on macOS.

### 13. **Requirements Updated 2025**
**File:** [`REQUIREMENTS_UPDATED_2025.md`](./REQUIREMENTS_UPDATED_2025.md)

Latest package versions for macOS:
- PyTorch 2.5.1
- Transformers 4.48.1
- Polars 1.19.0
- DuckDB 1.1.3
- etc.

---

## 🎯 Feature-Specific Guides

### 14. **AutoML Integration**
**Files:** 
- [`AUTOGLUON_GUIDE.md`](./AUTOGLUON_GUIDE.md)
- [`AUTO_SKLEARN_INTEGRATION.md`](./AUTO_SKLEARN_INTEGRATION.md)

**macOS advantages:**
- ✅ Real auto-sklearn (vs Windows custom implementation)
- ✅ Apple Silicon optimization in AutoGluon
- ✅ MPS acceleration for neural networks

### 15. **Unstructured Data Processing**
**File:** [`UNSTRUCTURED_DATA_FEATURES.md`](./UNSTRUCTURED_DATA_FEATURES.md)

**macOS support:**
- ✅ PDF extraction (PyPDF2, pdfplumber)
- ✅ Image OCR (Tesseract via pytesseract)
- ✅ Audio transcription (Whisper)
- ✅ Email parsing (.eml, .mbox)

**macOS dependencies:**
```bash
# Install Tesseract for OCR
brew install tesseract

# Install ffmpeg for audio
brew install ffmpeg
```

### 16. **Executive Report Generation**
**Files:** 
- [`EXECUTIVE_REPORT_GUIDE.md`](./EXECUTIVE_REPORT_GUIDE.md)
- [`ENHANCED_EXPORT_IMPLEMENTATION.md`](./ENHANCED_EXPORT_IMPLEMENTATION.md)

**macOS PDF generation:**
- ✅ Uses ReportLab (works on macOS)
- ✅ Supports macOS system fonts
- ✅ Quick Look integration (spacebar preview)

---

## 🔬 Advanced Topics

### 17. **Large Dataset Improvements**
**File:** [`LARGE_DATASET_IMPROVEMENTS.md`](./LARGE_DATASET_IMPROVEMENTS.md)

**macOS optimizations:**
- Polars streaming (spill to disk)
- DuckDB with SSD optimization
- External drive support
- Memory management

### 18. **Token Limit Fix**
**File:** [`TOKEN_LIMIT_FIX.md`](./TOKEN_LIMIT_FIX.md)

Context window management (same on all platforms).

---

## 📊 Tools & Capabilities

### 19. **Complete Tools Catalog** ⭐ NEW!
**File:** [`COMPLETE_TOOLS_CATALOG.md`](./COMPLETE_TOOLS_CATALOG.md)

**All 150+ tools work on macOS:**
- ✅ Data cleaning (14 tools)
- ✅ Model training (16 tools)
- ✅ Statistical inference (34 tools)
- ✅ Advanced modeling (22 tools)
- ✅ AutoML (5 tools)
- ✅ Deep learning (3 tools)
- ✅ Time series (2 tools)
- ✅ And more...

### 20. **14-Stage Workflow**
**File:** [`14_STAGE_WORKFLOW_IMPLEMENTATION.md`](./14_STAGE_WORKFLOW_IMPLEMENTATION.md)

Professional data science workflow (platform-agnostic).

---

## 🐛 Troubleshooting

### Common macOS Issues

**1. Permission Denied**
```bash
chmod 755 ~/Documents/DataScienceAgent
chmod -R u+rw ~/Documents/DataScienceAgent
```

**2. Python Not Found**
```bash
# Install via Homebrew
brew install python@3.12

# Add to PATH
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**3. uv Not Found**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

**4. Port Already in Use**
```bash
# Find process using port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port
export PORT=8081
```

**5. Tesseract Not Found (OCR)**
```bash
brew install tesseract
```

**6. FFmpeg Not Found (Audio)**
```bash
brew install ffmpeg
```

---

## 🎨 macOS-Specific Features

### Spotlight Integration
Reports and plots in `~/Documents/` are automatically indexed by Spotlight.

### Quick Look Support
- PDF reports support Quick Look (spacebar in Finder)
- PNG plots can be previewed
- JSON manifests are viewable

### Finder Integration
```bash
# Create alias on Desktop
ln -s ~/Documents/DataScienceAgent ~/Desktop/DataScienceAgent

# Open in Finder
open ~/Documents/DataScienceAgent
```

### Time Machine Backup
Files in `~/Documents/` are automatically backed up by Time Machine.

### iCloud Integration (Optional)
```bash
# Sync reports to iCloud Drive
AGENT_REPORTS_DIR=~/Library/Mobile Documents/com~apple~CloudDocs/DataScienceReports
```

---

## 📖 Additional Resources

### Online Documentation
- **Installation:** Start with `INSTALLATION.md`
- **Folder Config:** See `MACOS_FOLDER_CONFIGURATION.md`
- **GPU Setup:** Check `GPU_ACCELERATION_GUIDE.md`
- **Tools Reference:** Browse `COMPLETE_TOOLS_CATALOG.md`

### Getting Help
1. Check troubleshooting sections in each guide
2. Review `WINDOWS_COMPATIBILITY.md` for platform differences
3. See `QUICK_START.md` for common workflows

---

## ✅ macOS Setup Checklist

**System Requirements:**
- [ ] macOS 11+ (Big Sur or later)
- [ ] Python 3.10+ (3.12+ recommended)
- [ ] 8GB+ RAM (16GB recommended)
- [ ] 5GB+ free disk space

**Installation Steps:**
- [ ] Install Homebrew
- [ ] Install Python 3.12
- [ ] Install uv package manager
- [ ] Clone repository
- [ ] Copy `env.template` to `.env`
- [ ] Configure `AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent`
- [ ] Add `OPENAI_API_KEY`
- [ ] Run `uv sync`
- [ ] Start server: `python main.py`

**Optional Enhancements:**
- [ ] Install Tesseract for OCR: `brew install tesseract`
- [ ] Install FFmpeg for audio: `brew install ffmpeg`
- [ ] Configure external drive (if needed)
- [ ] Setup Time Machine backup
- [ ] Create Desktop alias for easy access

---

## 🚀 Quick Reference

**Start Server:**
```bash
python main.py
# or
uv run python main.py
```

**Verify Configuration:**
```bash
python -c "from data_science.large_data_config import print_config; print_config()"
```

**Check GPU (Apple Silicon):**
```bash
python -c "import torch; print(f'MPS: {torch.backends.mps.is_available()}')"
```

**View Workspace:**
```bash
open ~/Documents/DataScienceAgent/.uploaded/_workspaces/
```

---

## 📝 Summary

**macOS is Fully Supported!**

- ✅ **150+ tools** all work on macOS
- ✅ **Same workspace structure** as Windows
- ✅ **Configurable paths** via `.env`
- ✅ **Apple Silicon GPU** support (MPS)
- ✅ **Real auto-sklearn** (vs Windows custom)
- ✅ **Homebrew integration**
- ✅ **Spotlight & Quick Look** support
- ✅ **Time Machine** backup compatible
- ✅ **iCloud Drive** integration (optional)

**Key Advantage:**
macOS gets the real `auto-sklearn` package, while Windows uses a custom implementation. Otherwise, features are identical!

---

**Last Updated:** October 24, 2025  
**Platform:** macOS 11+ (Big Sur and later)  
**Total Documentation Files:** 43 files with macOS references

