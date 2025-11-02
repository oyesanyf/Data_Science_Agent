# 🐧 Linux Setup Guide

Complete guide for installing and configuring the Data Science Agent on Linux (Ubuntu, Debian, Fedora, RHEL, Arch, and more).

---

## 📋 Quick Start

### One-Line Install (Ubuntu/Debian)
```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/data-science-agent/main/install.sh | bash
```

### Manual Quick Setup
```bash
# 1. Install Python 3.12+
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip git

# 2. Install uv (fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# 3. Clone and setup
git clone <repo-url>
cd data-science-agent
cp env.template .env

# 4. Configure .env
nano .env
# Add:
# AGENT_UPLOAD_DIR=~/.local/share/data-science-agent
# OPENAI_API_KEY=sk-your-key-here

# 5. Install and run
uv sync
python main.py
```

---

## 🎯 Linux Distribution Guides

### Ubuntu / Debian

**Tested on:** Ubuntu 20.04, 22.04, 24.04 LTS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.12 python3.12-venv python3-pip \
    git curl build-essential libssl-dev libffi-dev \
    python3-dev tesseract-ocr ffmpeg

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Clone and setup
git clone <repo-url>
cd data-science-agent
uv sync

# Configure
cp env.template .env
nano .env  # Add your API key

# Run
python main.py
```

---

### Fedora / RHEL / CentOS

**Tested on:** Fedora 38, 39, RHEL 9

```bash
# Update system
sudo dnf update -y

# Install dependencies
sudo dnf install -y python3.12 python3-devel python3-pip \
    git curl gcc gcc-c++ openssl-devel libffi-devel \
    tesseract ffmpeg

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Clone and setup
git clone <repo-url>
cd data-science-agent
uv sync

# Configure
cp env.template .env
nano .env  # Add your API key

# Run
python main.py
```

---

### Arch Linux

**Tested on:** Arch Linux, Manjaro

```bash
# Update system
sudo pacman -Syu

# Install dependencies
sudo pacman -S python python-pip git curl base-devel \
    openssl libffi tesseract ffmpeg

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Clone and setup
git clone <repo-url>
cd data-science-agent
uv sync

# Configure
cp env.template .env
nano .env  # Add your API key

# Run
python main.py
```

---

## 📁 Linux Folder Structure

### XDG Base Directory Specification

**Recommended for Linux:**
```bash
# Edit .env
AGENT_UPLOAD_DIR=~/.local/share/data-science-agent
```

**Creates:**
```
~/.local/share/data-science-agent/
└── .uploaded/
    └── _workspaces/
        └── <dataset>/<timestamp>/
            ├── uploads/
            ├── data/
            ├── models/
            ├── reports/
            ├── plots/
            ├── metrics/
            ├── indexes/
            ├── logs/
            ├── tmp/
            ├── manifests/
            └── unstructured/
```

### Alternative Locations

**User Documents (visible):**
```bash
AGENT_UPLOAD_DIR=~/Documents/DataScienceAgent
```

**Custom location:**
```bash
AGENT_UPLOAD_DIR=/mnt/data/data-science-agent
```

**Shared multi-user (with permissions):**
```bash
AGENT_UPLOAD_DIR=/opt/data-science-agent
sudo mkdir -p /opt/data-science-agent
sudo chown $USER:$USER /opt/data-science-agent
```

---

## 🐳 Docker Installation (Recommended for Production)

### Using Docker Compose

**1. Create `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  data-science-agent:
    image: data-science-agent:latest
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_UPLOAD_DIR=/data
    volumes:
      - ./data:/data
      - ./models:/app/.uploaded/_workspaces
    restart: unless-stopped
```

**2. Build and run:**
```bash
# Set API key
export OPENAI_API_KEY=sk-your-key-here

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Dockerfile

**Build:**
```bash
docker build -t data-science-agent .
```

**Run:**
```bash
docker run -d \
  -p 8080:8080 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -v $(pwd)/data:/data \
  --name data-science-agent \
  data-science-agent
```

---

## 🎮 GPU Support (NVIDIA)

### CUDA Setup

**1. Install NVIDIA Drivers:**
```bash
# Ubuntu/Debian
sudo apt install -y nvidia-driver-535

# Fedora
sudo dnf install -y akmod-nvidia

# Check installation
nvidia-smi
```

**2. Install CUDA Toolkit:**
```bash
# Ubuntu 22.04
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-12-3-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

# Add to PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

**3. Verify GPU:**
```bash
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```

### Docker with GPU

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Run with GPU
docker run -d \
  --gpus all \
  -p 8080:8080 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -v $(pwd)/data:/data \
  --name data-science-agent \
  data-science-agent
```

---

## 🔧 Configuration

### Environment Variables (`.env` file)

```bash
# Linux XDG-compliant paths
AGENT_UPLOAD_DIR=~/.local/share/data-science-agent

# Optional: Custom temp directory
DUCKDB_TEMP_DIR=/tmp/duckdb_spill

# API Keys
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-key-here  # For ensemble mode

# GPU (if available)
CUDA_VISIBLE_DEVICES=0  # Use first GPU
# CUDA_VISIBLE_DEVICES=-1  # Force CPU
```

### Systemd Service (Run as Service)

**Create service file:**
```bash
sudo nano /etc/systemd/system/data-science-agent.service
```

**Add:**
```ini
[Unit]
Description=Data Science Agent
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/data-science-agent
Environment="PATH=/home/youruser/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="OPENAI_API_KEY=sk-your-key-here"
ExecStart=/home/youruser/.local/bin/uv run python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable data-science-agent
sudo systemctl start data-science-agent

# Check status
sudo systemctl status data-science-agent

# View logs
sudo journalctl -u data-science-agent -f
```

---

## 🔐 Security

### Firewall Configuration

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

**Firewalld (Fedora/RHEL):**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### Reverse Proxy (Nginx)

**Install Nginx:**
```bash
sudo apt install -y nginx  # Ubuntu/Debian
sudo dnf install -y nginx  # Fedora/RHEL
```

**Configure:**
```bash
sudo nano /etc/nginx/sites-available/data-science-agent
```

**Add:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/data-science-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
sudo certbot renew --dry-run
```

---

## 🛠️ Linux-Specific Features

### Auto-sklearn (Full Support)

**Linux is the primary platform for auto-sklearn:**
```bash
# Install with auto-sklearn
pip install -r requirements.txt
pip install -r requirements-linux.txt

# Verify
python -c "import autosklearn; print('auto-sklearn installed!')"
```

**Windows users:** Get custom implementation (works great!)  
**macOS users:** Real auto-sklearn works!  
**Linux users:** Full native support! ✅

### Large Dataset Optimization

**DuckDB with NVMe optimization:**
```bash
# Use fast SSD for temp files
DUCKDB_TEMP_DIR=/mnt/nvme/duckdb_spill
```

**Polars streaming with tmpfs:**
```bash
# Use RAM disk for maximum speed
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=8G tmpfs /mnt/ramdisk
DUCKDB_TEMP_DIR=/mnt/ramdisk/duckdb_spill
```

### Process Monitoring

**htop with color:**
```bash
sudo apt install htop
htop
```

**GPU monitoring:**
```bash
watch -n 1 nvidia-smi
```

**Resource limits:**
```bash
# Limit memory (8GB)
ulimit -v 8388608

# Check limits
ulimit -a
```

---

## 🐛 Troubleshooting

### Common Issues

**1. Python version too old**
```bash
# Check version
python3 --version

# Install Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

**2. Permission denied**
```bash
# Fix permissions
chmod 755 ~/.local/share/data-science-agent
chmod -R u+rw ~/.local/share/data-science-agent
```

**3. Port already in use**
```bash
# Find process
sudo lsof -i :8080

# Kill process
sudo kill -9 <PID>

# Or use different port
export PORT=8081
```

**4. Module not found**
```bash
# Reinstall dependencies
uv sync

# Or with pip
pip install -r requirements.txt
```

**5. CUDA not found**
```bash
# Check CUDA
nvcc --version

# Add to PATH
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

**6. Out of memory**
```bash
# Check memory
free -h

# Use swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📊 Performance Tuning

### CPU Optimization

```bash
# Install performance governor
sudo apt install cpufrequtils

# Set performance mode
sudo cpufreq-set -g performance

# Check
cpufreq-info
```

### Memory Settings

```bash
# Increase shared memory for large datasets
sudo sysctl -w kernel.shmmax=17179869184
sudo sysctl -w kernel.shmall=4194304

# Make permanent
echo "kernel.shmmax=17179869184" | sudo tee -a /etc/sysctl.conf
echo "kernel.shmall=4194304" | sudo tee -a /etc/sysctl.conf
```

### Disk I/O

```bash
# Check I/O scheduler
cat /sys/block/sda/queue/scheduler

# Set to deadline for SSDs
echo deadline | sudo tee /sys/block/sda/queue/scheduler

# Or noop for NVMe
echo noop | sudo tee /sys/block/nvme0n1/queue/scheduler
```

---

## 🔄 Updates

### Update Agent

```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv sync

# Restart service
sudo systemctl restart data-science-agent
```

### Update System

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# Fedora
sudo dnf update -y

# Arch
sudo pacman -Syu
```

---

## 📦 Package Dependencies

### Required

- Python 3.10+ (3.12+ recommended)
- Git
- Build tools (gcc, g++, make)
- OpenSSL
- libffi

### Optional (for full features)

- **Tesseract OCR:** `sudo apt install tesseract-ocr`
- **FFmpeg:** `sudo apt install ffmpeg`
- **CUDA:** For GPU acceleration
- **auto-sklearn:** `pip install -r requirements-linux.txt`

---

## ✅ Linux Advantages

**Why Linux is great for this agent:**

1. ✅ **Real auto-sklearn** (native support)
2. ✅ **Best GPU support** (NVIDIA CUDA)
3. ✅ **Systemd integration** (run as service)
4. ✅ **Docker support** (production deployments)
5. ✅ **Performance tuning** (full control)
6. ✅ **Large dataset optimization** (tmpfs, nvme)
7. ✅ **Free and open source** (Ubuntu, Debian, Fedora)
8. ✅ **SSH access** (remote deployment)
9. ✅ **Cron jobs** (automated tasks)
10. ✅ **No licensing costs** (unlike Windows Server)

---

## 🚀 Production Deployment Checklist

- [ ] Install on Ubuntu 22.04 LTS (or similar)
- [ ] Use Docker for isolation
- [ ] Setup systemd service for auto-restart
- [ ] Configure Nginx reverse proxy
- [ ] Enable SSL with Let's Encrypt
- [ ] Setup firewall (UFW)
- [ ] Configure automatic backups
- [ ] Enable monitoring (htop, nvidia-smi)
- [ ] Setup log rotation
- [ ] Test GPU acceleration
- [ ] Configure resource limits
- [ ] Setup automated updates

---

## 📚 Additional Resources

- **Installation:** See `INSTALLATION.md`
- **GPU Setup:** See `GPU_ACCELERATION_GUIDE.md`
- **Docker:** See `Dockerfile` and `docker-compose.yml`
- **Tools:** See `COMPLETE_TOOLS_CATALOG.md`
- **macOS:** See `MACOS_FOLDER_CONFIGURATION.md`
- **Windows:** See `WINDOWS_COMPATIBILITY.md`

---

## 🎯 Quick Commands Reference

```bash
# Start server
python main.py

# Start with UV
uv run python main.py

# Run as daemon
nohup python main.py > server.log 2>&1 &

# Check logs
tail -f server.log

# Stop server
pkill -f "python main.py"

# Restart systemd service
sudo systemctl restart data-science-agent

# Check GPU
nvidia-smi

# Check Python
python --version

# Verify config
python -c "from data_science.large_data_config import print_config; print_config()"
```

---

**Last Updated:** October 24, 2025  
**Tested Distributions:** Ubuntu 20.04/22.04/24.04, Fedora 38/39, Debian 11/12, Arch Linux  
**Minimum Requirements:** Python 3.10+, 4GB RAM, 5GB disk space

