# 🐧 Linux Documentation Index

Complete guide to all Linux-related documentation for the Data Science Agent.

---

## 📚 Main Linux Documentation

### 1. **Linux Setup Guide** ⭐ NEW!
**File:** [`LINUX_SETUP_GUIDE.md`](./LINUX_SETUP_GUIDE.md)

**What it covers:**
- ✅ Distribution-specific installation (Ubuntu, Fedora, Arch)
- ✅ XDG-compliant folder structure
- ✅ Docker deployment (production-ready)
- ✅ GPU setup (NVIDIA CUDA)
- ✅ Systemd service configuration
- ✅ Nginx reverse proxy
- ✅ SSL with Let's Encrypt
- ✅ Performance tuning
- ✅ Troubleshooting guide

**Quick Setup (Ubuntu/Debian):**
```bash
sudo apt install -y python3.12 python3-pip git
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo-url> && cd data-science-agent
cp env.template .env
nano .env  # Add AGENT_UPLOAD_DIR=~/.local/share/data-science-agent
uv sync && python main.py
```

---

## 🐧 Distribution-Specific Guides

### Ubuntu / Debian

**Tested:** Ubuntu 20.04, 22.04, 24.04 LTS

**Quick Install:**
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip \
    git curl build-essential libssl-dev libffi-dev python3-dev \
    tesseract-ocr ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

### Fedora / RHEL / CentOS

**Tested:** Fedora 38, 39, RHEL 9

**Quick Install:**
```bash
sudo dnf install -y python3.12 python3-devel python3-pip \
    git curl gcc gcc-c++ openssl-devel libffi-devel \
    tesseract ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Arch Linux

**Tested:** Arch Linux, Manjaro

**Quick Install:**
```bash
sudo pacman -S python python-pip git curl base-devel \
    openssl libffi tesseract ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 📁 Linux Folder Structure

### XDG Base Directory Specification (Recommended)

```bash
# In .env file:
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
            └── ...
```

**Follows Linux standards:**
- `~/.local/share/` - User-specific data files
- `~/.config/` - Configuration files
- `~/.cache/` - Cache files (use for DuckDB temp)
- `/tmp/` - Temporary files

---

## 🐳 Docker Deployment

### Why Docker on Linux?

- ✅ **Isolation:** Containerized environment
- ✅ **Portability:** Works on any Linux distribution
- ✅ **Scalability:** Easy to scale horizontally
- ✅ **Production-ready:** Industry standard
- ✅ **GPU support:** NVIDIA Container Toolkit

### Quick Docker Setup

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Build and run
docker build -t data-science-agent .
docker run -d -p 8080:8080 \
  -e OPENAI_API_KEY=sk-your-key \
  -v $(pwd)/data:/data \
  data-science-agent
```

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  data-science-agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/data
    restart: unless-stopped
```

**Run:**
```bash
docker-compose up -d
```

---

## 🎮 GPU Support (NVIDIA)

### CUDA Installation

**Ubuntu/Debian:**
```bash
# Install NVIDIA drivers
sudo apt install -y nvidia-driver-535

# Install CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.0-545.23.06-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-3-local_*.deb
sudo apt-get update
sudo apt-get -y install cuda

# Verify
nvidia-smi
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
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
docker run --gpus all -d -p 8080:8080 data-science-agent
```

---

## 🔧 Production Features

### Systemd Service (Auto-Start)

**Create service:**
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
Environment="OPENAI_API_KEY=sk-your-key-here"
ExecStart=/home/youruser/.local/bin/uv run python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable:**
```bash
sudo systemctl enable data-science-agent
sudo systemctl start data-science-agent
sudo systemctl status data-science-agent
```

### Nginx Reverse Proxy

**Install and configure:**
```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/data-science-agent
```

**Add:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/data-science-agent /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### SSL/TLS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo certbot renew --dry-run
```

---

## 🔐 Security

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Firewall (Firewalld)

```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SELinux (RHEL/Fedora)

```bash
# Check status
sestatus

# Set to permissive (if needed)
sudo setenforce 0

# Make permanent
sudo nano /etc/selinux/config
# Set: SELINUX=permissive
```

---

## 🛠️ Linux Advantages

### Why Linux is Best for This Agent

| Feature | Linux | Windows | macOS |
|---------|-------|---------|-------|
| **auto-sklearn** | ✅ Native | ❌ Custom | ✅ Native |
| **GPU (NVIDIA)** | ✅ Best | ✅ Good | ⚠️ eGPU only |
| **Docker** | ✅ Native | ⚠️ WSL2 | ⚠️ VM |
| **Production** | ✅ Systemd | ⚠️ Services | ⚠️ launchd |
| **Performance** | ✅ Best | ⚠️ Good | ✅ Good |
| **Cost** | ✅ Free | ❌ Licensed | ❌ Hardware |
| **SSH Access** | ✅ Native | ⚠️ PowerShell | ✅ Native |
| **Scalability** | ✅ Excellent | ⚠️ Good | ⚠️ Limited |

### Linux-Exclusive Features

1. **Real auto-sklearn:** Full native support
2. **Best GPU performance:** NVIDIA CUDA optimized
3. **Docker native:** No virtualization overhead
4. **Systemd:** Robust service management
5. **Performance tuning:** Full kernel control
6. **SSH deployment:** Remote server access
7. **Cron jobs:** Automated scheduling
8. **Process limits:** Fine-grained resource control
9. **Custom kernels:** Ultimate optimization
10. **Free:** No licensing costs

---

## 📊 Performance Optimization

### CPU Settings

```bash
# Set performance governor
sudo cpufreq-set -g performance

# Check
cpufreq-info
```

### Memory Tuning

```bash
# Increase shared memory
sudo sysctl -w kernel.shmmax=17179869184
sudo sysctl -w kernel.shmall=4194304

# Add swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Disk I/O

```bash
# Check scheduler
cat /sys/block/sda/queue/scheduler

# Set to deadline for SSDs
echo deadline | sudo tee /sys/block/sda/queue/scheduler

# Or noop for NVMe
echo noop | sudo tee /sys/block/nvme0n1/queue/scheduler
```

### Large Datasets

```bash
# Use tmpfs for maximum speed
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=8G tmpfs /mnt/ramdisk
export DUCKDB_TEMP_DIR=/mnt/ramdisk/duckdb_spill
```

---

## 📦 Package Management

### Requirements Files

| File | Platform | Purpose |
|------|----------|---------|
| `requirements.txt` | All | Core dependencies |
| `requirements-linux.txt` | Linux/macOS | auto-sklearn |
| `requirements-gpu.txt` | All | GPU packages |

**Install:**
```bash
# Base
pip install -r requirements.txt

# With auto-sklearn (Linux/macOS)
pip install -r requirements-linux.txt

# With GPU support
pip install -r requirements-gpu.txt
```

---

## 🐛 Troubleshooting

### Common Linux Issues

**1. Permission denied:**
```bash
chmod 755 ~/.local/share/data-science-agent
chmod -R u+rw ~/.local/share/data-science-agent
```

**2. Port in use:**
```bash
sudo lsof -i :8080
sudo kill -9 <PID>
```

**3. Python not found:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12
```

**4. CUDA not found:**
```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

**5. Out of memory:**
```bash
free -h
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**6. Module not found:**
```bash
uv sync
# or
pip install -r requirements.txt
```

---

## 📚 Related Documentation

**Core Guides:**
- [`INSTALLATION.md`](./INSTALLATION.md) - Cross-platform installation
- [`INSTALLATION_GUIDE.md`](./INSTALLATION_GUIDE.md) - Detailed setup
- [`LINUX_SETUP_GUIDE.md`](./LINUX_SETUP_GUIDE.md) - Linux-specific

**Platform Guides:**
- [`MACOS_FOLDER_CONFIGURATION.md`](./MACOS_FOLDER_CONFIGURATION.md) - macOS setup
- [`WINDOWS_COMPATIBILITY.md`](./WINDOWS_COMPATIBILITY.md) - Windows notes

**Feature Guides:**
- [`GPU_ACCELERATION_GUIDE.md`](./GPU_ACCELERATION_GUIDE.md) - GPU setup
- [`COMPLETE_TOOLS_CATALOG.md`](./COMPLETE_TOOLS_CATALOG.md) - All 150+ tools
- [`DOCKER_DEPLOYMENT.md`](./DOCKER_DEPLOYMENT.md) - Docker guide

---

## ✅ Linux Setup Checklist

**System Requirements:**
- [ ] Linux distribution (Ubuntu 20.04+, Fedora 38+, Arch, etc.)
- [ ] Python 3.10+ (3.12+ recommended)
- [ ] 4GB+ RAM (8GB+ for large datasets)
- [ ] 5GB+ disk space
- [ ] Internet connection

**Installation:**
- [ ] Update system packages
- [ ] Install Python 3.12
- [ ] Install build tools (gcc, make)
- [ ] Install uv package manager
- [ ] Clone repository
- [ ] Create `.env` from template
- [ ] Set `AGENT_UPLOAD_DIR=~/.local/share/data-science-agent`
- [ ] Add `OPENAI_API_KEY`
- [ ] Run `uv sync`
- [ ] Start server: `python main.py`

**Optional (Production):**
- [ ] Install Docker
- [ ] Setup systemd service
- [ ] Configure Nginx reverse proxy
- [ ] Enable SSL with Let's Encrypt
- [ ] Setup firewall (UFW/firewalld)
- [ ] Configure GPU (if available)
- [ ] Install Tesseract (OCR)
- [ ] Install FFmpeg (audio)
- [ ] Setup monitoring
- [ ] Configure backups

---

## 🚀 Quick Reference

**Start server:**
```bash
python main.py
```

**With UV:**
```bash
uv run python main.py
```

**As daemon:**
```bash
nohup python main.py > server.log 2>&1 &
```

**Systemd:**
```bash
sudo systemctl start data-science-agent
sudo systemctl status data-science-agent
sudo journalctl -u data-science-agent -f
```

**Docker:**
```bash
docker-compose up -d
docker-compose logs -f
```

**Check configuration:**
```bash
python -c "from data_science.large_data_config import print_config; print_config()"
```

**Check GPU:**
```bash
nvidia-smi
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

---

## 📝 Summary

**Linux: The Best Platform for This Agent!**

- ✅ **150+ tools** - All fully supported
- ✅ **Real auto-sklearn** - Native support (vs Windows custom)
- ✅ **Best GPU** - NVIDIA CUDA optimized
- ✅ **Docker native** - Production deployments
- ✅ **Systemd** - Robust service management
- ✅ **Free & Open Source** - No licensing costs
- ✅ **SSH access** - Remote deployment
- ✅ **Performance tuning** - Full kernel control
- ✅ **XDG-compliant** - Follows Linux standards

**Recommended Setup:**
- **Desktop:** Ubuntu 24.04 LTS
- **Server:** Ubuntu 22.04 LTS Server
- **Container:** Docker with Ubuntu base
- **GPU:** Ubuntu with CUDA 12.x
- **Production:** Docker Compose + Nginx + Let's Encrypt

---

**Last Updated:** October 24, 2025  
**Tested Distributions:** Ubuntu, Fedora, Debian, Arch, RHEL, CentOS  
**Total Files with Linux References:** 113+

