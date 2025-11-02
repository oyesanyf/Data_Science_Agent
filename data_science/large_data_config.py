"""
Large Dataset Configuration & Environment Variables
Handles GB+ datasets without memory spikes or size caps.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# Upload & Storage Configuration
# ============================================================================

# Upload directory (sandboxed, configurable)
# Default under the package folder to avoid polluting project root
# Supports absolute overrides via AGENT_UPLOAD_DIR
# [CRITICAL] MUST be .uploaded (with dot) - never "uploaded" without dot
DEFAULT_UPLOAD_DIR = (Path(__file__).parent / ".uploaded").as_posix()
_upload_dir_from_env = os.getenv("AGENT_UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
UPLOAD_ROOT = Path(os.path.expanduser(_upload_dir_from_env)).resolve()

# [CRITICAL] Validate that UPLOAD_ROOT ends with .uploaded (never allow "uploaded" without dot)
# This ensures workspace paths are ALWAYS under .uploaded/_workspaces (not uploaded/_workspaces)
if UPLOAD_ROOT.name != ".uploaded":
    # Check if .uploaded exists in parent directory
    parent = UPLOAD_ROOT.parent
    dot_uploaded = parent / ".uploaded"
    
    if dot_uploaded.exists() and dot_uploaded.is_dir():
        logger.warning(f"[PATH ENFORCEMENT] UPLOAD_ROOT was '{UPLOAD_ROOT}' but .uploaded exists at '{dot_uploaded}', using .uploaded")
        UPLOAD_ROOT = dot_uploaded.resolve()
    elif str(UPLOAD_ROOT).endswith("uploaded") and not str(UPLOAD_ROOT).endswith(".uploaded"):
        # Path ends with "uploaded" but not ".uploaded" - fix it
        # If it's the data_science directory, use data_science/.uploaded
        if parent.exists():
            dot_uploaded = parent / ".uploaded"
            logger.warning(f"[PATH FIX] UPLOAD_ROOT was '{UPLOAD_ROOT}' (missing dot). Creating/using '{dot_uploaded}'")
            dot_uploaded.mkdir(exist_ok=True)
            UPLOAD_ROOT = dot_uploaded.resolve()
        else:
            # Fallback: use package directory/.uploaded
            package_dir = Path(__file__).parent
            dot_uploaded = package_dir / ".uploaded"
            logger.warning(f"[PATH FIX] Using package directory .uploaded: {dot_uploaded}")
            UPLOAD_ROOT = dot_uploaded.resolve()
    
    # Final validation - ensure it's .uploaded
    if UPLOAD_ROOT.name != ".uploaded":
        logger.error(f"[PATH ERROR] UPLOAD_ROOT must end with '.uploaded', got: '{UPLOAD_ROOT}'. This will cause workspace path errors!")
        # Force to package/.uploaded as last resort
        package_dir = Path(__file__).parent
        UPLOAD_ROOT = (package_dir / ".uploaded").resolve()
        logger.info(f"[PATH FORCE] Forced UPLOAD_ROOT to: {UPLOAD_ROOT}")

# Log final UPLOAD_ROOT for verification (at module load time)
logger.info(f"[CONFIG] UPLOAD_ROOT set to: {UPLOAD_ROOT} (must end with .uploaded)")

# Workspace root (defaults to {UPLOAD_ROOT}/_workspaces)
WORKSPACES_ROOT = Path(os.path.expanduser(
    os.getenv("AGENT_WORKSPACES_DIR", str(UPLOAD_ROOT / "_workspaces"))
)).resolve()

# Models directory (defaults to {WORKSPACES_ROOT}/models or custom path)
MODELS_ROOT = Path(os.path.expanduser(
    os.getenv("AGENT_MODELS_DIR", "")
)).resolve() if os.getenv("AGENT_MODELS_DIR") else None

# Reports directory (defaults to {WORKSPACES_ROOT}/reports or custom path)
REPORTS_ROOT = Path(os.path.expanduser(
    os.getenv("AGENT_REPORTS_DIR", "")
)).resolve() if os.getenv("AGENT_REPORTS_DIR") else None

# Plots directory (defaults to {WORKSPACES_ROOT}/plots or custom path)
PLOTS_ROOT = Path(os.path.expanduser(
    os.getenv("AGENT_PLOTS_DIR", "")
)).resolve() if os.getenv("AGENT_PLOTS_DIR") else None

# Upload streaming buffer size (MB)
UPLOAD_CHUNK_MB = int(os.getenv("UPLOAD_CHUNK_MB", "4"))

# Parquet row group size (MB) - larger = better compression, less random access
PARQUET_ROWGROUP_MB = int(os.getenv("PARQUET_ROWGROUP_MB", "256"))

# ============================================================================
# Data Processing Configuration
# ============================================================================

# Profiling sample size (rows) - for Great Expectations, stats
PROFILE_SAMPLE_ROWS = int(os.getenv("PROFILE_SAMPLE_ROWS", "500000"))

# Enable Polars streaming mode (spills to disk for huge datasets)
POLARS_STREAMING = os.getenv("POLARS_STREAMING", "true").lower() == "true"

# Enable DuckDB spill to disk
DUCKDB_SPILL = os.getenv("DUCKDB_SPILL", "true").lower() == "true"

# DuckDB memory limit (GB)
DUCKDB_MEMORY_LIMIT = os.getenv("DUCKDB_MEMORY_LIMIT", "4GB")

# DuckDB temp directory for spilling
# Expands ~ for user home directory (e.g., ~/Library/Caches/... on macOS)
DUCKDB_TEMP_DIR = os.path.expanduser(os.getenv("DUCKDB_TEMP_DIR", "/tmp/duckdb_spill"))

# ============================================================================
# Model Training Configuration
# ============================================================================

# AutoML time limit (seconds) - longer for large datasets
AUTOML_TIME_LIMIT = int(os.getenv("AUTOML_TIME_LIMIT", "1800"))

# SHAP sample size (rows) - subsample for large datasets
SHAP_SAMPLE_ROWS = int(os.getenv("SHAP_SAMPLE_ROWS", "200000"))

# Use incremental learning for datasets larger than this (rows)
INCREMENTAL_LEARNING_THRESHOLD = int(os.getenv("INCREMENTAL_LEARNING_THRESHOLD", "1000000"))

# Batch size for incremental learning
INCREMENTAL_BATCH_SIZE = int(os.getenv("INCREMENTAL_BATCH_SIZE", "10000"))

# ============================================================================
# LLM & Rate Limiting Configuration
# ============================================================================

# LiteLLM max retries
LITELLM_MAX_RETRIES = int(os.getenv("LITELLM_MAX_RETRIES", "4"))

# Circuit breaker failure threshold
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))

# Circuit breaker cooldown (seconds)
CIRCUIT_BREAKER_COOLDOWN = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN", "300"))

# ============================================================================
# Security & Privacy Configuration
# ============================================================================

# Maximum filename length
MAX_FILENAME_LENGTH = int(os.getenv("MAX_FILENAME_LENGTH", "160"))

# Allowed file extensions (CSV, compressed, Parquet)
ALLOWED_EXTENSIONS = {
    '.csv', '.csv.gz', '.csv.zst', '.parquet', 
    '.txt', '.json', '.tsv', '.xlsx'
}

# Log absolute paths? (debug only, disable in production)
LOG_ABSOLUTE_PATHS = os.getenv("LOG_ABSOLUTE_PATHS", "false").lower() == "true"

# ============================================================================
# Observability Configuration
# ============================================================================

# Structured JSON logging
STRUCTURED_LOGGING = os.getenv("STRUCTURED_LOGGING", "true").lower() == "true"

# Log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================================
# Data Size Thresholds (for intelligent tool selection)
# ============================================================================

# Small dataset (use pandas, simple models)
SMALL_DATASET_THRESHOLD = int(os.getenv("SMALL_DATASET_THRESHOLD", "1000"))

# Medium dataset (use AutoGluon with moderate time)
MEDIUM_DATASET_THRESHOLD = int(os.getenv("MEDIUM_DATASET_THRESHOLD", "10000"))

# Large dataset (use streaming, incremental learning)
LARGE_DATASET_THRESHOLD = int(os.getenv("LARGE_DATASET_THRESHOLD", "1000000"))

# High dimensionality threshold (trigger feature selection)
HIGH_DIMENSIONALITY_THRESHOLD = int(os.getenv("HIGH_DIMENSIONALITY_THRESHOLD", "50"))

# ============================================================================
# Helper Functions
# ============================================================================

def get_optimal_time_limit(num_rows: int) -> int:
    """Get optimal AutoML time limit based on dataset size."""
    if num_rows < SMALL_DATASET_THRESHOLD:
        return 60  # 1 minute for small datasets
    elif num_rows < MEDIUM_DATASET_THRESHOLD:
        return 120  # 2 minutes for medium datasets
    elif num_rows < LARGE_DATASET_THRESHOLD:
        return 300  # 5 minutes for large datasets
    else:
        return AUTOML_TIME_LIMIT  # 30 minutes for huge datasets


def should_use_incremental_learning(num_rows: int) -> bool:
    """Determine if incremental learning should be used."""
    return num_rows >= INCREMENTAL_LEARNING_THRESHOLD


def should_use_streaming(num_rows: int) -> bool:
    """Determine if streaming mode should be used."""
    return num_rows >= LARGE_DATASET_THRESHOLD


def get_shap_sample_size(num_rows: int) -> int:
    """Get appropriate SHAP sample size based on dataset."""
    return min(num_rows, SHAP_SAMPLE_ROWS)


def print_config():
    """Print current configuration (for debugging)."""
    print("=" * 70)
    print("LARGE DATASET CONFIGURATION")
    print("=" * 70)
    print("\nFolder Structure:")
    print(f"  Upload Root: {UPLOAD_ROOT}")
    print(f"  Workspaces Root: {WORKSPACES_ROOT}")
    if MODELS_ROOT:
        print(f"  Models Root (custom): {MODELS_ROOT}")
    if REPORTS_ROOT:
        print(f"  Reports Root (custom): {REPORTS_ROOT}")
    if PLOTS_ROOT:
        print(f"  Plots Root (custom): {PLOTS_ROOT}")
    print(f"  DuckDB Temp: {DUCKDB_TEMP_DIR}")
    print("\nData Processing:")
    print(f"  Upload Chunk Size: {UPLOAD_CHUNK_MB} MB")
    print(f"  Parquet Row Group: {PARQUET_ROWGROUP_MB} MB")
    print(f"  Profile Sample: {PROFILE_SAMPLE_ROWS:,} rows")
    print(f"  Polars Streaming: {POLARS_STREAMING}")
    print(f"  DuckDB Spill: {DUCKDB_SPILL}")
    print(f"  DuckDB Memory: {DUCKDB_MEMORY_LIMIT}")
    print("\nModel Training:")
    print(f"  AutoML Time Limit: {AUTOML_TIME_LIMIT}s")
    print(f"  SHAP Sample: {SHAP_SAMPLE_ROWS:,} rows")
    print(f"  Incremental Learning Threshold: {INCREMENTAL_LEARNING_THRESHOLD:,} rows")
    print("\nReliability:")
    print(f"  Circuit Breaker: {CIRCUIT_BREAKER_THRESHOLD} failures, {CIRCUIT_BREAKER_COOLDOWN}s cooldown")
    print("=" * 70)


# Initialize directories
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)

# Verification function - can be called to verify paths are correct
def verify_paths() -> dict:
    """
    Verify that all paths are correctly configured with .uploaded (not uploaded).
    
    Returns:
        dict with verification results
    """
    results = {
        "upload_root_valid": UPLOAD_ROOT.name == ".uploaded",
        "upload_root_path": str(UPLOAD_ROOT),
        "workspaces_root_path": str(WORKSPACES_ROOT),
        "expected_workspace_pattern": ".uploaded/_workspaces",
        "workspace_has_dot_uploaded": ".uploaded" in str(WORKSPACES_ROOT),
    }
    
    if not results["upload_root_valid"]:
        logger.error(f"[PATH VERIFICATION FAILED] UPLOAD_ROOT should end with '.uploaded' but got: {UPLOAD_ROOT.name}")
    
    if not results["workspace_has_dot_uploaded"]:
        logger.error(f"[PATH VERIFICATION FAILED] WORKSPACES_ROOT should contain '.uploaded', got: {WORKSPACES_ROOT}")
    
    return results

# Create custom root directories if specified
if MODELS_ROOT:
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
if REPORTS_ROOT:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
if PLOTS_ROOT:
    PLOTS_ROOT.mkdir(parents=True, exist_ok=True)

# Create DuckDB temp directory if needed
if DUCKDB_SPILL and not Path(DUCKDB_TEMP_DIR).exists():
    Path(DUCKDB_TEMP_DIR).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print_config()

