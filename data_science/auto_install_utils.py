"""
Centralized Auto-Install Utility for Runtime Dependency Management

This module provides automatic installation of missing packages when tools are called.
It handles package name mappings (pip name vs import name) and provides user-friendly feedback.
"""

import subprocess
import sys
import importlib
import logging
from typing import Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Track installation attempts to avoid redundant work
_installation_cache: Dict[str, bool] = {}


# Comprehensive mapping of tools to their required packages
# Format: {tool_name: {'import_name': 'package_name', 'pip_name': 'pip_package_name', 'version': 'version_spec'}}
TOOL_DEPENDENCIES: Dict[str, Dict[str, str]] = {
    # Feature Engineering
    'auto_feature_synthesis': {
        'import_name': 'featuretools',
        'pip_name': 'featuretools',
        'version': '>=1.0.0'
    },
    'feature_importance_stability': {
        'import_name': 'featuretools',
        'pip_name': 'featuretools',
        'version': '>=1.0.0'
    },
    
    # Responsible AI
    'fairness_report': {
        'import_name': 'fairlearn',
        'pip_name': 'fairlearn',
        'version': '>=0.9.0'
    },
    'fairness_mitigation_grid': {
        'import_name': 'fairlearn',
        'pip_name': 'fairlearn',
        'version': '>=0.9.0'
    },
    
    # Data & Model Drift
    'drift_profile': {
        'import_name': 'evidently',
        'pip_name': 'evidently',
        'version': '>=0.4.0'
    },
    'data_quality_report': {
        'import_name': 'evidently',
        'pip_name': 'evidently',
        'version': '>=0.4.0'
    },
    
    # Causal Inference
    'causal_identify': {
        'import_name': 'dowhy',
        'pip_name': 'dowhy',
        'version': '>=0.11.0'
    },
    'causal_estimate': {
        'import_name': 'dowhy',
        'pip_name': 'dowhy',
        'version': '>=0.11.0'
    },
    
    # Imbalanced Learning
    'rebalance_fit': {
        'import_name': 'imblearn',
        'pip_name': 'imbalanced-learn',
        'version': '>=0.11.0'
    },
    'calibrate_probabilities': {
        'import_name': 'imblearn',
        'pip_name': 'imbalanced-learn',
        'version': '>=0.11.0'
    },
    
    # Time Series
    'ts_prophet_forecast': {
        'import_name': 'prophet',
        'pip_name': 'prophet',
        'version': '>=1.1.0'
    },
    'ts_backtest': {
        'import_name': 'prophet',
        'pip_name': 'prophet',
        'version': '>=1.1.0'
    },
    
    # Embeddings & Vector Search
    'embed_text_column': {
        'import_name': 'sentence_transformers',
        'pip_name': 'sentence-transformers',
        'version': '>=2.0.0'
    },
    'vector_search': {
        'import_name': 'faiss',
        'pip_name': 'faiss-cpu',  # Falls back to faiss-gpu if GPU available
        'version': '>=1.7.0'
    },
    
    # Data Versioning
    'dvc_init_local': {
        'import_name': 'dvc',
        'pip_name': 'dvc',
        'version': '>=3.0.0'
    },
    'dvc_track': {
        'import_name': 'dvc',
        'pip_name': 'dvc',
        'version': '>=3.0.0'
    },
    
    # Post-Deploy Monitoring
    'monitor_drift_fit': {
        'import_name': 'alibi_detect',
        'pip_name': 'alibi-detect',
        'version': '>=0.11.0'
    },
    'monitor_drift_score': {
        'import_name': 'alibi_detect',
        'pip_name': 'alibi-detect',
        'version': '>=0.11.0'
    },
    
    # Fast Query & EDA
    'duckdb_query': {
        'import_name': 'duckdb',
        'pip_name': 'duckdb',
        'version': '>=0.9.0'
    },
    'polars_profile': {
        'import_name': 'polars',
        'pip_name': 'polars',
        'version': '>=0.19.0'
    },
    
    # Hyperparameter Optimization
    'optuna_tune': {
        'import_name': 'optuna',
        'pip_name': 'optuna',
        'version': '>=3.0.0'
    },
    
    # Data Validation
    'ge_auto_profile': {
        'import_name': 'great_expectations',
        'pip_name': 'great-expectations',
        'version': '>=0.18.0'
    },
    'ge_validate': {
        'import_name': 'great_expectations',
        'pip_name': 'great-expectations',
        'version': '>=0.18.0'
    },
    
    # Experiment Tracking
    'mlflow_start_run': {
        'import_name': 'mlflow',
        'pip_name': 'mlflow',
        'version': '>=2.0.0'
    },
    'mlflow_log_metrics': {
        'import_name': 'mlflow',
        'pip_name': 'mlflow',
        'version': '>=2.0.0'
    },
    'mlflow_end_run': {
        'import_name': 'mlflow',
        'pip_name': 'mlflow',
        'version': '>=2.0.0'
    },
    
    # AutoML
    'smart_autogluon_automl': {
        'import_name': 'autogluon',
        'pip_name': 'autogluon.tabular',
        'version': '>=0.8.0'
    },
    'smart_autogluon_timeseries': {
        'import_name': 'autogluon',
        'pip_name': 'autogluon.timeseries',
        'version': '>=0.8.0'
    },
    'auto_sklearn_classify': {
        'import_name': 'autosklearn',
        'pip_name': 'auto-sklearn',
        'version': '>=0.15.0'
    },
    'auto_sklearn_regress': {
        'import_name': 'autosklearn',
        'pip_name': 'auto-sklearn',
        'version': '>=0.15.0'
    },
    
    # Deep Learning (handled separately due to GPU considerations)
    'train_dl_classifier': {
        'import_name': 'torch',
        'pip_name': 'torch',
        'version': '>=2.0.0'
    },
    'train_dl_regressor': {
        'import_name': 'torch',
        'pip_name': 'torch',
        'version': '>=2.0.0'
    },
}


def ensure_package(
    package_name: str,
    pip_name: Optional[str] = None,
    version: Optional[str] = None,
    tool_name: Optional[str] = None,
    silent: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Ensure a package is available, auto-installing if needed.
    NEVER RAISES EXCEPTIONS - always returns (bool, Optional[str]).
    
    Args:
        package_name: Python import name (e.g., 'featuretools')
        pip_name: pip package name if different (e.g., 'imbalanced-learn' for 'imblearn')
        version: Version specifier (e.g., '>=1.0.0')
        tool_name: Name of tool requesting this package (for better error messages)
        silent: If True, suppress output (except errors)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Check cache first
        cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
        if cache_key in _installation_cache:
            if _installation_cache[cache_key]:
                return True, None
            else:
                return False, f"Package {package_name} installation previously failed"
    except Exception as e:
        logger.warning(f"[AUTO-INSTALL] Cache check failed: {e}")
        # Continue anyway - not critical
    
        # Try to import first
        try:
            importlib.import_module(package_name)
            _installation_cache[cache_key] = True
            return True, None
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"[AUTO-INSTALL] Import check error (non-critical): {e}")
            # Continue to installation attempt
    except Exception as e:
        # If cache lookup failed, continue anyway
        logger.debug(f"[AUTO-INSTALL] Error during cache lookup: {e}")
    
    # Try to import first (outside cache block)
    try:
        importlib.import_module(package_name)
        try:
            cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
            _installation_cache[cache_key] = True
        except Exception:
            pass
        return True, None
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"[AUTO-INSTALL] Import check error (non-critical): {e}")
        # Continue to installation attempt
    
    # Determine install command
    install_name = pip_name or package_name
    if version:
        install_spec = f"{install_name}{version}"
    else:
        install_spec = install_name
    
    # Try to auto-install
    tool_info = f" (for {tool_name})" if tool_name else ""
    if not silent:
        print(f"📦 Installing {install_name}{version or ''}...{tool_info}")
    
    try:
        # Use quiet install but show progress
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', install_spec],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = (result.stderr or result.stdout or "Unknown error")[:200]
            if not silent:
                try:
                    logger.error(f"Failed to install {install_name}: {error_msg}")
                except Exception:
                    pass
            try:
                cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
                _installation_cache[cache_key] = False
            except Exception:
                pass
            return False, f"Failed to install {install_name}: {error_msg}"
        
        # Verify installation by trying to import
        try:
            importlib.import_module(package_name)
            if not silent:
                try:
                    print(f"✅ Successfully installed {install_name}!")
                except Exception:
                    pass
            try:
                cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
                _installation_cache[cache_key] = True
            except Exception:
                pass
            return True, None
        except ImportError as e:
            error_msg = f"Installed {install_name} but cannot import {package_name}: {str(e)[:100]}"
            if not silent:
                try:
                    logger.error(error_msg)
                except Exception:
                    pass
            try:
                cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
                _installation_cache[cache_key] = False
            except Exception:
                pass
            return False, error_msg
        except Exception as verify_error:
            error_msg = f"Verification failed after install: {str(verify_error)[:100]}"
            try:
                cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
                _installation_cache[cache_key] = False
            except Exception:
                pass
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = f"Installation of {install_name} timed out after 5 minutes"
        if not silent:
            try:
                logger.error(error_msg)
            except Exception:
                pass
        try:
            cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
            _installation_cache[cache_key] = False
        except Exception:
            pass
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to install {install_name}: {str(e)[:200]}"
        if not silent:
            try:
                logger.error(error_msg)
            except Exception:
                pass
        try:
            cache_key = f"{package_name}_{pip_name or package_name}_{version or ''}"
            _installation_cache[cache_key] = False
        except Exception:
            pass
        return False, error_msg


def ensure_tool_dependencies(tool_name: str, silent: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Ensure all dependencies for a specific tool are available.
    
    Args:
        tool_name: Name of the tool (matches keys in TOOL_DEPENDENCIES)
        silent: If True, suppress output (except errors)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if tool_name not in TOOL_DEPENDENCIES:
        # Tool has no special dependencies or unknown tool
        return True, None
    
    deps = TOOL_DEPENDENCIES[tool_name]
    success, error = ensure_package(
        package_name=deps['import_name'],
        pip_name=deps.get('pip_name'),
        version=deps.get('version'),
        tool_name=tool_name,
        silent=silent
    )
    
    return success, error


def auto_install_package(
    package_name: str,
    pip_name: Optional[str] = None,
    version: Optional[str] = None
) -> bool:
    """
    Legacy wrapper for backward compatibility with existing code.
    Use ensure_package() for new code.
    
    Args:
        package_name: Python import name
        pip_name: pip package name if different
        version: Version specifier
    
    Returns:
        True if package is available (installed or auto-installed), False otherwise
    """
    success, _ = ensure_package(package_name, pip_name, version, silent=False)
    return success


# Export for use in other modules
__all__ = [
    'ensure_package',
    'ensure_tool_dependencies',
    'auto_install_package',
    'TOOL_DEPENDENCIES'
]

