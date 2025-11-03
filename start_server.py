#!/usr/bin/env python3
"""
Data Science Agent Startup Script (Python)
- Kills any existing process on port 8080
- Sets SERVE_WEB_INTERFACE=true
- Runs "uv sync" to install all 90+ tools' dependencies
- Launches the app with "uv run python main.py"

Note: This script relies on 'uv sync' to handle dependency installation.
The main.py file has auto_install_dependencies() which checks for:
  - Core packages (litellm, openai, pandas, numpy, sklearn, etc.)
  - Advanced tools (optuna, mlflow, fairlearn, evidently, etc.)
  
IMPORTANT: Some packages have different pip names vs import names:
  - pip: imbalanced-learn    → import: imblearn
  - pip: sentence-transformers → import: sentence_transformers  
  - pip: alibi-detect         → import: alibi_detect
  - pip: faiss-cpu/faiss-gpu  → import: faiss
  - pip: python-dotenv        → import: dotenv
  - pip: scikit-learn         → import: sklearn

CRITICAL VERSION CONSTRAINTS:
  - numpy MUST be <2.0 (opencv-python requires numpy 1.x)
  - opencv-python >=4.8.0 required by AutoGluon multimodal
  - If you get "RuntimeError: empty_like method already has a different docstring"
    → Run: fix_numpy_opencv.bat to fix numpy version
"""

import os
import sys
import time
import signal
import subprocess
from typing import List, Set

PORT = 8080

def detect_gpu() -> bool:
    """
    Detect if GPU is available on this system.
    Checks for NVIDIA GPU via nvidia-smi and CUDA availability.
    """
    # Check for nvidia-smi (NVIDIA GPU)
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_name = result.stdout.strip().split('\n')[0]
            print(f"[GPU] DETECTED: {gpu_name}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    
    # Check via PyTorch (if already installed)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[GPU] DETECTED via PyTorch: {gpu_name}")
            return True
    except ImportError:
        pass
    
    print("[CPU] MODE: No GPU detected, using CPU")
    return False


def banner() -> None:
    print()
    print("=" * 60)
    print("Starting Data Science Agent with Web Interface")
    print("=" * 60)
    print()

def run_cmd(cmd: List[str], check: bool = False, capture: bool = True, shell: bool = False):
    """Run a command and optionally capture its stdout; returns (code, stdout)."""
    try:
        if capture:
            proc = subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
            return proc.returncode, proc.stdout
        else:
            proc = subprocess.run(cmd, check=check, shell=shell)
            return proc.returncode, ""
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.CalledProcessError as e:
        # If check=True and non-zero, capture output in e.stdout (Python 3.11+) else fallback
        out = getattr(e, "stdout", "") or ""
        return e.returncode, out if out else str(e)

def find_pids_on_port(port: int) -> Set[int]:
    """Try multiple strategies to find PIDs bound to a TCP port (cross-platform)."""
    pids: Set[int] = set()
    is_windows = os.name == "nt"

    if is_windows:
        # netstat -ano (IPv4/IPv6) and filter lines with :port
        code, out = run_cmd(["netstat", "-ano"], capture=True)
        if code == 0 and out:
            for line in out.splitlines():
                # Typical line:  TCP    0.0.0.0:8080   0.0.0.0:0   LISTENING   1234
                # Or:            TCP    [::]:8080      [::]:0      LISTENING   1234
                if f":{port}" in line:
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        try:
                            pids.add(int(parts[-1]))
                        except ValueError:
                            pass

        # Fallback to PowerShell Get-NetTCPConnection
        if not pids:
            ps_cmd = [
                "powershell", "-NoProfile", "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty OwningProcess -Unique"
            ]
            code, out = run_cmd(ps_cmd, capture=True)
            if code == 0 and out:
                for tok in out.split():
                    if tok.strip().isdigit():
                        pids.add(int(tok.strip()))
    else:
        # Unix-like: try lsof first (most reliable)
        code, out = run_cmd(["lsof", "-t", f"-i:{port}"], capture=True)
        if code == 0 and out:
            for tok in out.split():
                if tok.strip().isdigit():
                    pids.add(int(tok.strip()))

        # Fallback to netstat parsing
        if not pids:
            code, out = run_cmd(["netstat", "-ltnp"], capture=True)
            if code == 0 and out:
                # Lines look like: tcp 0 0 0.0.0.0:8080 0.0.0.0:* LISTEN 1234/python
                for line in out.splitlines():
                    if f":{port} " in line or line.rstrip().endswith(f":{port}"):
                        # Extract the PID/program (usually last column)
                        parts = line.split()
                        if parts:
                            last = parts[-1]
                            # Format often "PID/comm"
                            if "/" in last:
                                pid_str = last.split("/", 1)[0]
                                if pid_str.isdigit():
                                    pids.add(int(pid_str))
    return pids

def kill_pids(pids: Set[int]) -> None:
    if not pids:
        return
    print(f"Found existing process(es) on port {PORT}: {', '.join(map(str, pids))}. Stopping...")

    is_windows = os.name == "nt"
    for pid in pids:
        try:
            if is_windows:
                # Use taskkill for child tree as well
                run_cmd(["taskkill", "/F", "/T", "/PID", str(pid)], capture=False)
            else:
                # Graceful then force
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    # Give processes a moment to exit
    time.sleep(2)

    # Force-kill any survivors (Unix)
    if not is_windows:
        survivors = find_pids_on_port(PORT)
        for pid in survivors:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
        time.sleep(1)

    print("[OK] Existing server stopped\n")

def clear_pycache() -> None:
    """
    Clear Python bytecode cache to prevent stale imports.
    Removes all __pycache__ directories recursively.
    """
    import shutil
    from pathlib import Path
    
    print("Clearing Python bytecode cache...")
    cache_found = False
    
    # Find and remove all __pycache__ directories
    for cache_dir in Path(".").rglob("__pycache__"):
        if cache_dir.is_dir():
            cache_found = True
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
            except Exception:
                pass  # Silently ignore errors
    
    if cache_found:
        print("[OK] Cache cleared (prevents stale imports)")
    else:
        print("[OK] Cache already clean")
    print()

def ensure_uv_sync(has_gpu: bool = False) -> None:
    if has_gpu:
        print("Syncing dependencies with uv (150+ ML tools + GPU acceleration)...")
    else:
        print("Syncing dependencies with uv (150+ ML tools)...")
    
    code, out = run_cmd(["uv", "sync"], capture=True)
    if code != 0:
        print()
        print("[ERROR] Failed to sync dependencies with uv. Make sure 'uv' is installed and on PATH.")
        if out:
            print(out.strip())
        print()
        print("Install uv:")
        print("  - Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        print("  - macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  - Or: pip install uv")
        print()
        print("Docs: https://docs.astral.sh/uv/")
        sys.exit(1)
    
    if has_gpu:
        print("[OK] All dependencies synced successfully!")
        print("     [GPU] MODE: 150+ tools ready with GPU acceleration")
        print("     All tools now use ADK-safe wrappers for optimal performance!")
        print("     AutoML, XGBoost, LightGBM will use GPU for 5-10x speedup!")
        print("     [OK] Non-streaming tools ONLY (streaming disabled - conflicts with interactive workflow)\n")
    else:
        print("[OK] All dependencies synced successfully!")
        print("     [CPU] MODE: 150+ tools ready")
        print("     All tools now use ADK-safe wrappers for optimal performance!")
        print("     AutoML, Sklearn, Fairness, Drift, Causal, HPO, and more")
        print("     [OK] Non-streaming tools ONLY (streaming disabled - conflicts with interactive workflow)\n")

def main():
    banner()
    
    # Clear Python bytecode cache first
    clear_pycache()
    
    # Detect GPU
    print("Checking GPU availability...")
    has_gpu = detect_gpu()
    print()

    print(f"Checking for existing server on port {PORT}...")
    pids = find_pids_on_port(PORT)
    if pids:
        kill_pids(pids)

    # Set env for child processes
    os.environ["SERVE_WEB_INTERFACE"] = "true"
    os.environ["SKIP_DEPENDENCY_CHECK"] = "true"  # uv sync already handles dependencies
    # Also set environment variable to suppress warnings in ALL subprocesses
    os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources'

    ensure_uv_sync(has_gpu)

    print(f"Starting server on http://localhost:{PORT}")
    if has_gpu:
        print("[GPU] Acceleration enabled - training will be 5-10x faster!")
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()

    # Hand off to uv run python main.py
    # Use the current environment so SERVE_WEB_INTERFACE is inherited.
    try:
        proc = subprocess.run(["uv", "run", "python", "main.py"])
        sys.exit(proc.returncode)
    except FileNotFoundError:
        print("[ERROR] 'uv' not found on PATH. Please install uv: https://docs.astral.sh/uv/")
        sys.exit(127)

if __name__ == "__main__":
    main()
