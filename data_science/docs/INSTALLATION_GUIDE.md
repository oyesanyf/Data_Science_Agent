# 🚀 Complete Installation Guide - Data Science Agent

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installing UV Package Manager](#installing-uv-package-manager)
3. [Cloning the Repository](#cloning-the-repository)
4. [Setting Up the Environment](#setting-up-the-environment)
5. [Configuring API Keys](#configuring-api-keys)
6. [Installing Dependencies](#installing-dependencies)
7. [Running the Server](#running-the-server)
8. [Troubleshooting](#troubleshooting)
9. [Development Workflow](#development-workflow)

---

## 1. Prerequisites

### Required Software
- **Python**: 3.10 or higher
- **Git**: For cloning the repository
- **Windows/Linux/Mac**: Works on all platforms

### Hardware Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: 5GB free space
- **GPU** (optional): NVIDIA GPU with CUDA for faster training

### Check Your Python Version
```bash
python --version
# Should output: Python 3.10.x or higher
```

If Python is not installed or version is too old:
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Linux/Mac**: Use package manager (apt, brew, etc.)

---

## 2. Installing UV Package Manager

**UV** is a fast Python package installer and resolver (Rust-based, much faster than pip).

### Why UV?
- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic** dependency resolution
- 📦 **Built-in virtual environment** management
- 🚀 **Zero-config** for most projects

### Installation

#### Windows (PowerShell)
```powershell
# Install UV using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

#### Linux/Mac (Bash)
```bash
# Install UV using curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

#### Alternative: Using pip
```bash
pip install uv
```

### Expected Output
```
uv 0.5.x (or newer)
```

---

## 3. Cloning the Repository

### Step 1: Navigate to Your Projects Folder
```bash
# Windows
cd C:\Users\YourUsername\Projects

# Linux/Mac
cd ~/Projects
```

### Step 2: Clone the Repository
```bash
# If you have the repository URL
git clone https://github.com/yourusername/data_science_agent.git

# Navigate into the project
cd data_science_agent
```

### Step 3: Verify Project Structure
```bash
# List files (Windows)
dir

# List files (Linux/Mac)
ls -la
```

**Expected Structure**:
```
data_science_agent/
├── data_science/           # Main agent package
│   ├── agent.py           # Agent definition
│   ├── ds_tools.py        # Data science tools
│   ├── autogluon_tools.py # AutoGluon tools
│   └── ...
├── main.py                # FastAPI server entry point
├── pyproject.toml         # UV/pip dependencies
├── requirements.txt       # Pip requirements (fallback)
├── start_server.py        # Cross-platform startup script
├── start_server.ps1       # PowerShell startup script
├── start_server.bat       # Windows batch startup script
├── .env.example           # Environment variables template
└── README.md              # Project documentation
```

---

## 4. Setting Up the Environment

### Step 1: Create Python Virtual Environment (UV manages this automatically)

UV will automatically create and manage a virtual environment when you run `uv sync`.

**Optional: Manual venv creation**:
```bash
# If you prefer to create it manually first
uv venv

# Activate the virtual environment (optional, uv handles this)
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

---

## 5. Configuring API Keys

The Data Science Agent uses **OpenAI** and optionally **Google Gemini** for AI-powered features.

### Step 1: Copy Environment Template
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### Step 2: Get Your API Keys

#### OpenAI API Key (Required)
1. Go to [platform.openai.com](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-proj-...`)

#### Google Gemini API Key (Optional)
1. Go to [ai.google.dev](https://ai.google.dev/)
2. Click **"Get API key"**
3. Create a project in Google AI Studio
4. Copy the API key (starts with `AIzaSy...`)

### Step 3: Edit `.env` File
Open `.env` in a text editor and add your keys:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Optional: Google Gemini API Key (for fallback/alternative models)
GOOGLE_API_KEY=AIzaSy-your-actual-key-here

# Optional: Session service (leave as default for local development)
# SESSION_SERVICE_URI=

# Optional: Skip dependency check if using uv sync (set by startup scripts)
SKIP_DEPENDENCY_CHECK=false

# Optional: GPU settings (auto-detected)
# CUDA_VISIBLE_DEVICES=0
```

**⚠️ IMPORTANT**: Never commit `.env` to git! It's in `.gitignore`.

---

## 6. Installing Dependencies

### Method 1: Using UV (Recommended - Fast!)

```bash
# Sync all dependencies (creates venv + installs packages)
uv sync

# This will:
# 1. Create a virtual environment in .venv/
# 2. Install all dependencies from pyproject.toml
# 3. Lock dependency versions
# 4. Take ~30 seconds (vs 5+ minutes with pip)
```

**Expected Output**:
```
Resolved 87 packages in 1.2s
Installed 87 packages in 12.3s
 + google-adk==x.x.x
 + pandas==2.x.x
 + scikit-learn==1.x.x
 + ... (and 84 more)
```

### Method 2: Using pip (Fallback - Slower)

```bash
# Activate virtual environment first
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### GPU Support (Optional)

If you have an NVIDIA GPU and want GPU acceleration:

```bash
# After uv sync or pip install, add GPU libraries
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
uv pip install xgboost[gpu] lightgbm cupy-cuda12x faiss-gpu

# Or with pip:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install xgboost[gpu] lightgbm cupy-cuda12x faiss-gpu
```

**Check GPU availability**:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

---

## 7. Running the Server

### Method 1: Using Startup Scripts (Recommended - Easiest!)

The startup scripts automatically:
- Kill any existing processes on port 8080
- Run `uv sync` to ensure dependencies are up to date
- Clear Python cache (`__pycache__`)
- Detect GPU availability
- Set environment variables
- Start the server

#### Windows (PowerShell)
```powershell
# Navigate to project root
cd C:\harfile\data_science_agent

# Run the PowerShell script
.\start_server.ps1
```

#### Windows (Command Prompt / Batch)
```cmd
# Navigate to project root
cd C:\harfile\data_science_agent

# Run the batch script
start_server.bat
```

#### Linux/Mac or Cross-Platform (Python)
```bash
# Navigate to project root
cd ~/data_science_agent

# Run the Python startup script
python start_server.py
```

**Expected Output**:
```
🚀 Data Science Agent - Server Startup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Syncing dependencies with UV...
Resolved 87 packages in 0.3s
Audited 87 packages in 0.1s

🧹 Clearing Python cache...
Removed 12 __pycache__ directories

🔍 Checking GPU availability...
✅ GPU detected: NVIDIA GeForce RTX 3080

🌐 Starting server...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)

✅ Server is running!
   → Web UI: http://localhost:8080
   → API Docs: http://localhost:8080/docs
```

### Method 2: Using UV Run (Direct)

```bash
# Run the main.py directly with UV (auto-activates venv)
uv run python main.py
```

### Method 3: Using Python (Manual)

```bash
# Activate virtual environment first
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Run the server
python main.py
```

### Accessing the Web Interface

Once the server is running, open your browser:

**Main Interface**:
```
http://localhost:8080
```

**API Documentation** (Swagger UI):
```
http://localhost:8080/docs
```

---

## 8. Troubleshooting

### Issue 1: `uv: command not found`

**Cause**: UV not installed or not in PATH

**Solution**:
```bash
# Reinstall UV
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal/PowerShell
```

### Issue 2: Port 8080 Already in Use

**Error**: `[Errno 10048] error while attempting to bind on address`

**Solution**:
```bash
# Windows - Kill process on port 8080
netstat -ano | findstr :8080
taskkill /F /PID <PID_NUMBER>

# Linux/Mac - Kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or just run the startup script (it auto-kills for you)
.\start_server.ps1
```

### Issue 3: `ModuleNotFoundError: No module named 'litellm'`

**Cause**: Dependencies not installed or using wrong Python environment

**Solution**:
```bash
# Method 1: Use startup script (recommended)
.\start_server.ps1

# Method 2: Manual sync
uv sync

# Method 3: Force reinstall
uv pip install litellm --force-reinstall
```

### Issue 4: API Key Not Found

**Error**: `OPENAI_API_KEY not found in environment variables`

**Solution**:
```bash
# Check if .env file exists
# Windows
type .env

# Linux/Mac
cat .env

# If missing, create it from template
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac

# Edit .env and add your key
# OPENAI_API_KEY=sk-proj-your-key-here
```

### Issue 5: GPU Not Detected (If You Have GPU)

**Cause**: CUDA libraries not installed

**Solution**:
```bash
# Check CUDA availability
nvidia-smi

# If CUDA works but PyTorch doesn't detect it:
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

# Verify
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue 6: Slow First Startup

**Cause**: First-time model downloads (AutoGluon, transformers)

**Expected**: First startup may take 5-10 minutes to download pre-trained models

**Solution**: Wait for downloads to complete. Subsequent startups will be fast.

### Issue 7: `pkg_resources is deprecated` Warning

**Cause**: AutoGluon uses deprecated `pkg_resources`

**Solution**: Already suppressed in code, but if you see it:
```bash
# Set environment variable before starting
set PYTHONWARNINGS=ignore::UserWarning:pkg_resources   # Windows
export PYTHONWARNINGS=ignore::UserWarning:pkg_resources # Linux/Mac

# Or use startup script (already handles this)
.\start_server.ps1
```

---

## 9. Development Workflow

### Daily Development

```bash
# 1. Navigate to project
cd C:\harfile\data_science_agent

# 2. Pull latest changes (if working with a team)
git pull

# 3. Sync dependencies (if pyproject.toml changed)
uv sync

# 4. Start server
.\start_server.ps1

# 5. Make code changes
# Edit files in data_science/ folder

# 6. Server auto-reloads (Uvicorn watches for file changes)
# Just refresh browser or re-send API request

# 7. Test your changes
# Upload CSV in web UI and test tools
```

### Adding New Dependencies

```bash
# Add a new package using UV
uv add package-name

# Example: Add matplotlib
uv add matplotlib

# This automatically:
# - Installs the package
# - Updates pyproject.toml
# - Updates uv.lock file
```

### Updating Dependencies

```bash
# Update all dependencies to latest versions
uv sync --upgrade

# Update specific package
uv pip install --upgrade package-name
```

### Running Tests (If Available)

```bash
# Run tests with pytest
uv run pytest

# Or activate venv and run
.venv\Scripts\activate   # Windows
pytest
```

### Checking Installed Packages

```bash
# List all installed packages
uv pip list

# Show specific package info
uv pip show pandas
```

### Clearing Cache

```bash
# Clear Python bytecode cache
python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"

# Or just run startup script (does this automatically)
.\start_server.ps1
```

---

## 10. Project Structure Explained

```
data_science_agent/
├── .env                    # ⚠️ Your API keys (DO NOT COMMIT!)
├── .env.example            # Template for .env
├── .gitignore              # Git ignore rules
├── .venv/                  # Virtual environment (created by uv)
│
├── main.py                 # 🚀 Server entry point
├── pyproject.toml          # 📦 UV/pip dependencies & project config
├── requirements.txt        # 📦 Pip requirements (fallback)
├── requirements-gpu.txt    # 📦 GPU-specific dependencies
├── uv.lock                 # 🔒 Locked dependency versions (UV)
│
├── start_server.py         # 🖥️ Cross-platform startup script
├── start_server.ps1        # 🖥️ Windows PowerShell startup
├── start_server.bat        # 🖥️ Windows batch startup
├── clear_cache.ps1         # 🧹 Cache clearing utility
│
├── data_science/           # 🧠 Main agent package
│   ├── __init__.py
│   ├── agent.py           # Agent definition & tool registration
│   ├── ds_tools.py        # Core data science tools (80+ functions)
│   ├── autogluon_tools.py # AutoML tools
│   ├── extended_tools.py  # Advanced tools (fairness, drift, etc.)
│   ├── advanced_tools.py  # Statistical analysis tools
│   ├── deep_learning_tools.py # Deep learning tools
│   ├── auto_sklearn_tools.py  # Auto-sklearn integration
│   ├── chunk_aware_tools.py   # Large dataset handling
│   ├── large_data_handler.py  # Streaming uploads
│   ├── large_data_config.py   # Configuration
│   ├── circuit_breaker.py     # Service resilience
│   │
│   ├── .uploaded/         # 📁 Uploaded CSV files (temp)
│   ├── .export/           # 📁 Generated reports (organized by dataset)
│   │   ├── anagrams/
│   │   ├── tips/
│   │   └── ...
│   ├── .plot/             # 📁 Generated charts
│   └── models/            # 📁 Trained models (organized by dataset)
│       ├── anagrams/
│       │   ├── baseline_model.joblib
│       │   └── autogluon/
│       ├── tips/
│       └── ...
│
├── README.md              # 📖 Project overview
├── INSTALLATION_GUIDE.md  # 📖 This file
├── ORIGINAL_FILENAME_FIX_REVIEW.md  # 📖 Recent changes
├── SESSION_PERSISTENCE_TEST.md      # 📖 Testing docs
└── FINAL_REVIEW_SUMMARY.md          # 📖 Review summary
```

---

## 11. Quick Reference Commands

### UV Commands
| Command | Description |
|---------|-------------|
| `uv sync` | Install/update all dependencies |
| `uv sync --upgrade` | Update all packages to latest versions |
| `uv add <package>` | Add a new dependency |
| `uv pip install <package>` | Install package (like pip) |
| `uv pip list` | List installed packages |
| `uv run <command>` | Run command in project venv |
| `uv venv` | Create virtual environment |

### Server Commands
| Command | Description |
|---------|-------------|
| `.\start_server.ps1` | Start server (Windows PowerShell) |
| `start_server.bat` | Start server (Windows CMD) |
| `python start_server.py` | Start server (Cross-platform) |
| `uv run python main.py` | Start server (UV direct) |
| `Ctrl+C` | Stop server |

### Git Commands
| Command | Description |
|---------|-------------|
| `git status` | Check what changed |
| `git pull` | Get latest changes |
| `git add .` | Stage all changes |
| `git commit -m "message"` | Commit changes |
| `git push` | Push to remote |

---

## 12. Next Steps

Once your server is running:

1. **Upload a CSV file** via the web interface at `http://localhost:8080`
2. **Ask questions** about your data (e.g., "analyze this dataset")
3. **Train models** (the agent will suggest the best approach)
4. **Generate reports** (executive summaries with charts)
5. **Export results** (PDF reports, model files)

### Example Prompts to Try:
```
"Analyze this dataset and tell me about it"
"Train a model to predict [target_column]"
"What are the most important features?"
"Generate an executive report"
"Show me a correlation heatmap"
"Clean this data and handle missing values"
"Find outliers using clustering"
```

---

## 13. Getting Help

### Documentation
- **Project README**: `README.md`
- **API Docs**: `http://localhost:8080/docs` (when server running)
- **Tool Help**: In chat, type `help()` to see all 80 available tools

### Common Issues
- **Dependencies**: Run `uv sync` again
- **Port conflicts**: Run startup script (auto-kills old processes)
- **API keys**: Check `.env` file has valid keys
- **GPU not detected**: Install CUDA libraries

### Community
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions in GitHub Discussions

---

## ✅ Installation Checklist

- [ ] Python 3.10+ installed
- [ ] UV package manager installed
- [ ] Repository cloned
- [ ] `.env` file created with API keys
- [ ] Dependencies installed (`uv sync`)
- [ ] Server starts successfully
- [ ] Web interface accessible at `http://localhost:8080`
- [ ] Can upload CSV and run analysis

---

**🎉 Congratulations! You're ready to use the Data Science Agent!**

For questions or issues, check the troubleshooting section or open a GitHub issue.
