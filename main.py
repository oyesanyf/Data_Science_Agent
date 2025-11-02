# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file initializes a FastAPI application for Data Science agent
using get_fast_api_app() from ADK. Session service URI and a flag
for a web interface configured via environment variables.
It can then be run using Uvicorn, which listens on a port specified by
the PORT environment variable or defaults to 8080.
This approach offers more flexibility, particularly if you want to
embed Data Science agent within a custom FastAPI application.
It is used for Cloud Run deployment with standard gcloud run deploy command.
"""

import os
import sys
import warnings
import logging

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Suppress experimental warnings from ADK framework
warnings.filterwarnings('ignore', category=UserWarning, module='google.adk')

# Suppress pkg_resources deprecation warning from AutoGluon (they need to update to importlib.metadata)
# This catches warnings in main process and worker processes
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*pkg_resources.*', category=DeprecationWarning)

# Also set environment variable to suppress warnings in ALL subprocesses
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources'

def detect_gpu():
    """
    Detect if GPU is available on this system.
    Checks for NVIDIA GPU via nvidia-smi and CUDA availability.
    """
    import subprocess
    
    # Check for NVIDIA GPU
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(" GPU DETECTED: NVIDIA GPU found via nvidia-smi")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Check for CUDA via torch (if already installed)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f" GPU DETECTED: {gpu_name} (via PyTorch)")
            return True
    except ImportError:
        pass
    
    print(" CPU MODE: No GPU detected, using CPU")
    return False


def auto_install_dependencies():
    """
    Automatically check and install missing dependencies at startup.
    Detects GPU and installs GPU-accelerated versions when available.
    This ensures all required packages are available before the server starts.
    """
    import subprocess
    import importlib
    
    # If SKIP_DEPENDENCY_CHECK env var is set, skip this entirely
    # (uv sync already handles dependencies)
    if os.getenv("SKIP_DEPENDENCY_CHECK", "false").lower() == "true":
        print("\n[OK] Skipping dependency check (uv sync already ran)\n")
        return
    
    # Detect GPU availability
    has_gpu = detect_gpu()
    
    # Critical packages that must be available
    # Format: 'import_name': 'pip_package_spec'
    critical_packages = {
        'litellm': 'litellm>=1.55.10',
        'openai': 'openai>=1.59.7',
        'dotenv': 'python-dotenv>=1.0.1',
        'uvicorn': 'uvicorn',
        'fastapi': 'fastapi',
        'pandas': 'pandas>=2.0.0,<2.3.0',
        'numpy': 'numpy>=1.24,<2.0',  # Must be <2.0 for opencv compatibility
        'cv2': 'opencv-python>=4.8.0',  # Required by AutoGluon multimodal
        'sklearn': 'scikit-learn>=1.4.0',
        'optuna': 'optuna>=3.0.0',  # Bayesian hyperparameter optimization
        'great_expectations': 'great-expectations>=0.18.0',  # Data validation & quality
        'mlflow': 'mlflow>=2.0.0',  # Experiment tracking & model registry
        'fairlearn': 'fairlearn>=0.9.0',  # Responsible AI & fairness
        'evidently': 'evidently>=0.4.0',  # Data & model drift detection
        'dowhy': 'dowhy>=0.11.0',  # Causal inference
        'featuretools': 'featuretools>=1.0.0',  # Automated feature engineering
        'imblearn': 'imbalanced-learn>=0.11.0',  # Imbalanced data (imports as 'imblearn')
        'prophet': 'prophet>=1.1.0',  # Time series forecasting
        'sentence_transformers': 'sentence-transformers>=2.0.0',  # Text embeddings (imports as 'sentence_transformers')
        'dvc': 'dvc>=3.0.0',  # Data version control
        'alibi_detect': 'alibi-detect>=0.11.0',  # Model monitoring (imports as 'alibi_detect')
        'duckdb': 'duckdb>=0.9.0',  # Fast SQL queries
        'polars': 'polars>=0.19.0',  # Fast dataframes
        'langchain_text_splitters': 'langchain-text-splitters>=0.0.1',  # Text chunking for large documents
    }
    
    # Add GPU-specific or CPU-specific packages
    if has_gpu:
        print("\n GPU MODE: Installing GPU-accelerated packages...")
        critical_packages.update({
            'torch': 'torch>=2.0.0',  # PyTorch with CUDA
            'xgboost': 'xgboost[gpu]',  # XGBoost with GPU support
            'lightgbm': 'lightgbm',  # LightGBM (GPU support via cmake)
            'cupy': 'cupy-cuda12x',  # GPU-accelerated NumPy (CUDA 12.x, imports as 'cupy')
            'faiss': 'faiss-gpu>=1.7.0',  # GPU-accelerated vector search (imports as 'faiss')
        })
    else:
        print("\n CPU MODE: Installing CPU-optimized packages...")
        critical_packages.update({
            'torch': 'torch>=2.0.0',  # PyTorch CPU version
            'xgboost': 'xgboost>=2.0.0',  # XGBoost CPU version
            'lightgbm': 'lightgbm>=4.0.0',  # LightGBM CPU version
            'faiss': 'faiss-cpu>=1.7.0',  # CPU vector search (imports as 'faiss')
        })
    
    missing_packages = []
    
    print("\n" + "="*60)
    print("CHECKING DEPENDENCIES...")
    print("="*60)
    
    for module_name, package_spec in critical_packages.items():
        try:
            importlib.import_module(module_name)
            print(f" {module_name:20s} - OK")
        except ImportError:
            print(f" {module_name:20s} - MISSING")
            missing_packages.append(package_spec)
    
    if missing_packages:
        print("\n" + "="*60)
        print(f"INSTALLING {len(missing_packages)} MISSING PACKAGE(S)...")
        print("="*60)
        
        for package in missing_packages:
            print(f"\nInstalling {package}...")
            try:
                # Use uv if available (uv is a binary, not a Python module)
                try:
                    subprocess.check_call(['uv', 'pip', 'install', package],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to regular pip
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f" {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f" Failed to install {package}: {e}")
                sys.exit(1)
        
        print("\n" + "="*60)
        print("ALL DEPENDENCIES INSTALLED SUCCESSFULLY!")
        print("="*60 + "\n")
    else:
        print("\n All dependencies are already installed!\n")

# Auto-install missing dependencies before importing them
auto_install_dependencies()

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Suppress warnings about default values in Google AI function schemas
# These are expected and don't affect functionality
warnings.filterwarnings('ignore', message='Default value is not supported in function declaration schema')

# Load environment variables from .env file
load_dotenv()

# Print GPU status after dependencies are loaded
try:
    from data_science.gpu_config import print_gpu_status
    print_gpu_status()
except ImportError:
    print("[WARNING]  GPU detection unavailable")

# Enable verbose logging for debugging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging with detailed format
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# CRITICAL: Reduce LiteLLM logging to prevent system prompt spam
os.environ["LITELLM_LOG"] = "INFO"  # Changed from DEBUG to INFO
os.environ["LITELLM_LOG_LEVEL"] = "INFO"  # Explicit level setting

# Try to use Google Cloud Logging if credentials are available, otherwise use standard logging
try:
    from google.cloud import logging as google_cloud_logging
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception:
    # Fall back to standard Python logging for local development
    logger = logging.getLogger(__name__)

# Reduce verbose logging - only show important activity (not full prompts)
logging.getLogger("google_adk").setLevel(logging.INFO)  # Reduced from DEBUG
logging.getLogger("google.adk.tools").setLevel(logging.INFO)  # Reduced from DEBUG
logging.getLogger("google.adk.agents").setLevel(logging.INFO)  # Reduced from DEBUG - prevents prompt logging
logging.getLogger("google.adk.cli.fast_api").setLevel(logging.INFO)  # Reduced from DEBUG
logging.getLogger("LiteLLM").setLevel(logging.WARNING)  # Reduced from DEBUG - prevents full prompt logging
logging.getLogger("litellm").setLevel(logging.WARNING)  # Reduced from DEBUG - prevents full prompt logging
logging.getLogger("openai").setLevel(logging.WARNING)  # Prevent OpenAI SDK prompt logging
logging.getLogger("httpx").setLevel(logging.WARNING)  # Only show warnings/errors for HTTP
logging.getLogger("data_science").setLevel(logging.INFO)  # Reduced from DEBUG - still show tool activity
logging.getLogger("data_science.agent").setLevel(logging.INFO)  # Reduced from DEBUG
logging.getLogger("data_science.ds_tools").setLevel(logging.INFO)  # Reduced from DEBUG
logging.getLogger("matplotlib").setLevel(logging.WARNING)  # Suppress matplotlib DEBUG logs (plot spam)
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)  # Suppress font manager DEBUG logs
logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)  # Suppress harmless warnings

# Add colored output for better readability (optional, but helpful)
try:
    import colorlog
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logging.getLogger().handlers = [handler]
except ImportError:
    pass  # colorlog not installed, use default formatting

print("\n" + "="*60)
print("DATA SCIENCE AGENT - VERBOSE LOGGING ENABLED")
print("="*60)
print(f"Log Level: {LOG_LEVEL}")
print(f"LiteLLM Logging: ENABLED")
print(f"OpenAI Model: {os.getenv('OPENAI_MODEL', 'gpt-4o')}")
print(f"API Key Set: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")
print("="*60 + "\n")

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get session service URI from environment variables
session_service_uri = os.getenv("SESSION_SERVICE_URI", None)

# CRITICAL: Clean up the URI value (remove quotes, newlines, extra text)
if session_service_uri:
    # Strip whitespace and quotes
    session_service_uri = session_service_uri.strip().strip('"').strip("'")
    # Remove any newlines and text after them (corrupted .env file)
    if '\n' in session_service_uri:
        session_service_uri = session_service_uri.split('\n')[0].strip().strip('"').strip("'")
    # If it's empty after cleaning, set to None
    if not session_service_uri:
        session_service_uri = None
    else:
        print(f"[INFO] Using session service: {session_service_uri}")

# Get artifact service URI from environment variables (ADK supports GCS via gs://bucket-name)
artifact_service_uri = os.getenv("ARTIFACT_SERVICE_URI", None)
if artifact_service_uri:
    artifact_service_uri = artifact_service_uri.strip().strip('"').strip("'")
    if '\n' in artifact_service_uri:
        artifact_service_uri = artifact_service_uri.split('\n')[0].strip().strip('"').strip("'")
    if not artifact_service_uri:
        artifact_service_uri = None
    else:
        print(f"[INFO] Using artifact service: {artifact_service_uri}")
else:
    print("[INFO] Using in-memory artifact service (default) - set ARTIFACT_SERVICE_URI=gs://bucket-name for persistent storage")

# Get Enable Web interface serving flag from environment variables
# Set web=True if you intend to serve a web interface, False otherwise
web_interface_enabled = os.getenv("SERVE_WEB_INTERFACE", 'False').lower() in ('true', '1')

# Prepare arguments for get_fast_api_app
app_args = {
    "agents_dir": AGENT_DIR, 
    "web": web_interface_enabled
}

# Only include session_service_uri if it's provided
if session_service_uri:
    app_args["session_service_uri"] = session_service_uri

# Include artifact_service_uri if provided (ADK will use GcsArtifactService for gs:// URIs)
if artifact_service_uri:
    app_args["artifact_service_uri"] = artifact_service_uri
else:
    log_message = (
        "SESSION_SERVICE_URI not provided. Using in-memory session service instead. "
        "All sessions will be lost when the server restarts."
    )
    # Use appropriate logging method based on logger type
    if hasattr(logger, 'log_text'):
        logger.log_text(log_message, severity="WARNING")
    else:
        logger.warning(log_message)

# Initialize state database for UI sink
try:
    from data_science.state_store import init_db
    init_db()
    print("[OK] State database initialized for UI sink")
except Exception as e:
    print(f"[WARNING]  Failed to initialize state database: {e}")
    # Continue anyway - UI sink will gracefully degrade

# CRITICAL: Ensure database directory exists for ADK's session service
# ADK's DatabaseSessionService will try to create a database in this directory
try:
    from pathlib import Path
    import re
    
    db_dir_created = False
    
    # If session_service_uri is not set, ADK will use default SQLite database
    if not session_service_uri:
        # ADK default is typically 'sqlite:///adk_sessions.db' in the current directory
        # Ensure current directory is writable
        db_dir = Path(".")
        db_dir.mkdir(parents=True, exist_ok=True)
        print("[OK] Database directory verified for ADK session service (default location)")
        db_dir_created = True
    else:
        # If custom URI is set, extract and create directory if it's SQLite
        if "sqlite:" in session_service_uri:
            # Extract path from SQLite URI, handling various formats:
            # sqlite:///path/to/db.db
            # sqlite:///./path/to/db.db
            # sqlite:////absolute/path/to/db.db
            
            # Remove sqlite:/// prefix
            db_path_str = session_service_uri.replace('sqlite:///', '')
            
            # Handle ./ prefix
            if db_path_str.startswith('./'):
                db_path_str = db_path_str[2:]
            
            # Create Path object
            db_path = Path(db_path_str)
            
            # Create parent directory
            if db_path.parent and str(db_path.parent) != '.':
                db_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"[OK] Created database directory: {db_path.parent.absolute()}")
                db_dir_created = True
            else:
                # Database is in current directory
                print("[OK] Database will be created in current directory")
                db_dir_created = True
    
    if not db_dir_created:
        print("[WARNING] Could not determine database directory, using defaults")
        
except Exception as e:
    print(f"[WARNING] Error creating database directory: {e}")
    import traceback
    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
    # Continue anyway - will attempt database creation and fail more gracefully

# Create FastAPI app with appropriate arguments
app: FastAPI = get_fast_api_app(**app_args)

app.title = "data_science"
app.description = "Data Science Agent"

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
