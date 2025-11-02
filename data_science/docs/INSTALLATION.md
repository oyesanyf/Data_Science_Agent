# Installation Guide

Complete installation instructions for the Data Science Agent on all platforms.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Install](#quick-install)
- [Detailed Installation](#detailed-installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Verification](#verification)
- [Configuration](#configuration)
- [Docker Installation](#docker-installation)
- [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

Before installation, ensure you have:

### Required

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Git** ([Download](https://git-scm.com/downloads))

### Recommended

- **uv** package manager (will be installed if not present)
- **Visual Studio Code** or your preferred IDE
- **Windows Terminal** (Windows users)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 4 GB | 8 GB+ |
| **Disk Space** | 2 GB | 5 GB+ |
| **CPU** | 2 cores | 4+ cores |
| **OS** | Windows 10, macOS 11, Ubuntu 20.04 | Latest versions |

---

## ⚡ Quick Install

### One-Line Install (Linux/macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/data-science-agent/main/install.sh | bash
```

### One-Line Install (Windows PowerShell)

```powershell
irm https://raw.githubusercontent.com/yourusername/data-science-agent/main/install.ps1 | iex
```

### Manual Quick Install

```bash
# Clone repository
git clone https://github.com/yourusername/data-science-agent.git
cd data-science-agent

# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
# OR
irm https://astral.sh/uv/install.ps1 | iex      # Windows

# Install dependencies
uv sync

# Set API key
export OPENAI_API_KEY="your-api-key-here"  # Linux/Mac
$env:OPENAI_API_KEY="your-api-key-here"    # Windows

# Start server
uv run python main.py
```

---

## 📦 Detailed Installation

### Windows

#### 1. Install Python

```powershell
# Check if Python is installed
python --version

# If not installed, download from python.org
# Or use Windows Store (recommended)
```

#### 2. Install Git

```powershell
# Download from git-scm.com
# Or use winget
winget install Git.Git
```

#### 3. Clone Repository

```powershell
git clone https://github.com/yourusername/data-science-agent.git
cd data-science-agent
```

#### 4. Install uv Package Manager

```powershell
# Install uv
irm https://astral.sh/uv/install.ps1 | iex

# Verify installation
uv --version
```

#### 5. Create Virtual Environment & Install Dependencies

```powershell
# Install all dependencies
uv sync

# This creates .venv and installs all packages
```

#### 6. Set Environment Variables

**Option A: PowerShell (temporary)**
```powershell
$env:OPENAI_API_KEY="sk-your-api-key-here"
$env:SERVE_WEB_INTERFACE="true"
```

**Option B: Create .env file (persistent)**
```powershell
# Create .env file
@"
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
SERVE_WEB_INTERFACE=true
LOG_LEVEL=DEBUG
"@ | Out-File -FilePath .env -Encoding utf8
```

#### 7. Start the Server

```powershell
# Validate and start
.\start_with_validation.ps1

# Or start directly
$env:SERVE_WEB_INTERFACE='true'
uv run python main.py
```

#### 8. Access Web Interface

Open browser to: **http://localhost:8080**

---

### macOS

#### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python & Git

```bash
# Install Python
brew install python@3.12

# Install Git
brew install git
```

#### 3. Clone Repository

```bash
git clone https://github.com/yourusername/data-science-agent.git
cd data-science-agent
```

#### 4. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="$HOME/.cargo/bin:$PATH"

# Verify
uv --version
```

#### 5. Install Dependencies

```bash
uv sync
```

#### 6. Configure Environment

```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
SERVE_WEB_INTERFACE=true
LOG_LEVEL=DEBUG
EOF
```

#### 7. Start Server

```bash
# Validate code first
uv run python validate_code.py

# Start server
export SERVE_WEB_INTERFACE=true
uv run python main.py
```

#### 8. Access Web Interface

Open browser to: **http://localhost:8080**

---

### Linux (Ubuntu/Debian)

#### 1. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

#### 2. Install Python & Dependencies

```bash
# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install Git
sudo apt install git -y
```

#### 3. Clone Repository

```bash
git clone https://github.com/yourusername/data-science-agent.git
cd data-science-agent
```

#### 4. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
uv --version
```

#### 5. Install Dependencies

```bash
uv sync
```

#### 6. Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
SERVE_WEB_INTERFACE=true
LOG_LEVEL=DEBUG
EOF
```

#### 7. Start Server

```bash
# Validate code
uv run python validate_code.py

# Start server
export SERVE_WEB_INTERFACE=true
uv run python main.py
```

#### 8. Access Web Interface

Open browser to: **http://localhost:8080**

---

## ✅ Verification

### 1. Check Installation

```bash
# Verify Python
python --version  # Should show 3.12+

# Verify uv
uv --version

# Verify dependencies
uv pip list
```

### 2. Validate Code

```bash
uv run python validate_code.py
```

Expected output:
```
=== Data Science Agent - Code Validator ===

[1/3] Checking syntax errors...
[OK] data_science/agent.py
[OK] data_science/ds_tools.py
...

[OK] All validations passed!
```

### 3. Test Agent

```bash
# Start server
uv run python main.py

# In another terminal
curl http://localhost:8080/
```

### 4. Verify Tools

```python
# In Python
from data_science.agent import root_agent
print(f"Tools loaded: {len(root_agent.tools)}")
# Should show: Tools loaded: 44
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional (with defaults)
OPENAI_MODEL=gpt-4o
SERVE_WEB_INTERFACE=true
LOG_LEVEL=DEBUG
PORT=8080

# Advanced
USE_GEMINI=false
SESSION_SERVICE_URI=
LITELLM_LOG=DEBUG
```

### Configuration File

Edit `data_science/config.py` for advanced settings:

```python
# File size limits
MAX_FILE_SIZE_MB = 100
MAX_IMAGE_SIZE_MB = 10

# AutoML settings
DEFAULT_TIME_LIMIT = 60
DEFAULT_PRESET = 'medium_quality'

# Model paths
MODELS_DIR = 'data_science/models'
```

---

## 🐳 Docker Installation

### Using Docker

```bash
# Build image
docker build -t data-science-agent .

# Run container
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  data-science-agent
```

### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERVE_WEB_INTERFACE=true
    volumes:
      - ./data_science/models:/app/data_science/models
```

```bash
# Start with compose
docker-compose up -d
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Python Version Error

**Error**: `Python 3.12 or higher required`

**Solution**:
```bash
# Check version
python --version

# Install correct version
# Windows: Download from python.org
# macOS: brew install python@3.12
# Linux: sudo apt install python3.12
```

#### 2. uv Not Found

**Error**: `uv: command not found`

**Solution**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

#### 3. OpenAI API Key Error

**Error**: `API Key Set: NO`

**Solution**:
```bash
# Set environment variable
export OPENAI_API_KEY="sk-your-key"  # Linux/Mac
$env:OPENAI_API_KEY="sk-your-key"   # Windows

# Or create .env file
echo 'OPENAI_API_KEY=sk-your-key' > .env
```

#### 4. Port Already in Use

**Error**: `[Errno 10048] Address already in use`

**Solution**:
```bash
# Find process using port 8080
# Windows
netstat -ano | findstr :8080
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8080 | xargs kill -9

# Or use different port
export PORT=8081
```

#### 5. Module Import Errors

**Error**: `ModuleNotFoundError: No module named 'package'`

**Solution**:
```bash
# Reinstall dependencies
uv sync

# Or use pip
pip install -r requirements.txt
```

#### 6. Permission Errors (Linux/Mac)

**Error**: `Permission denied`

**Solution**:
```bash
# Fix file permissions
chmod +x start_with_validation.ps1
chmod +x validate_code.py

# Or run with sudo (not recommended)
sudo uv run python main.py
```

---

## 🔄 Updating

### Update to Latest Version

```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv sync

# Restart server
uv run python main.py
```

### Update Dependencies Only

```bash
# Update all packages
uv sync --upgrade

# Update specific package
uv pip install --upgrade package-name
```

---

## 🗑️ Uninstallation

### Complete Removal

```bash
# Stop server (Ctrl+C)

# Remove virtual environment
rm -rf .venv

# Remove repository
cd ..
rm -rf data-science-agent

# Uninstall uv (optional)
rm -rf ~/.cargo/bin/uv
```

---

## 📚 Next Steps

After installation:

1. **Read the Documentation** - See [README.md](README.md)
2. **Try Examples** - Check [TOOLS_USER_GUIDE.md](TOOLS_USER_GUIDE.md)
3. **Join Community** - Discord, GitHub Discussions
4. **Contribute** - See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 💬 Getting Help

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) section
2. Search [GitHub Issues](https://github.com/yourusername/data-science-agent/issues)
3. Ask in [Discussions](https://github.com/yourusername/data-science-agent/discussions)
4. Join our [Discord](https://discord.gg/your-invite)
5. Email support@example.com

---

<div align="center">

**🎉 Installation complete! Start analyzing data with AI! 🎉**

[Back to README](README.md) | [Quick Start Guide](QUICK_REFERENCE.md) | [Tools Guide](TOOLS_USER_GUIDE.md)

</div>

---

Last updated: 2025-01-15

