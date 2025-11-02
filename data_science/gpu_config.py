"""
GPU Configuration and Utilities
Detects GPU availability and provides helper functions for GPU-accelerated training.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Global GPU availability flag (set at startup)
GPU_AVAILABLE = False
GPU_DEVICE_NAME = None


def detect_and_set_gpu():
    """
    Detect GPU availability and set global flag.
    Called automatically at module import.
    """
    global GPU_AVAILABLE, GPU_DEVICE_NAME
    
    # Check environment variable override
    force_cpu = os.getenv('FORCE_CPU', 'false').lower() == 'true'
    if force_cpu:
        logger.info(" GPU disabled by FORCE_CPU environment variable")
        GPU_AVAILABLE = False
        return False
    
    # Check for nvidia-smi (NVIDIA GPU)
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            GPU_DEVICE_NAME = result.stdout.strip().split('\n')[0]
            logger.info(f" GPU DETECTED: {GPU_DEVICE_NAME}")
            GPU_AVAILABLE = True
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    
    # Check via PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            GPU_DEVICE_NAME = torch.cuda.get_device_name(0)
            GPU_AVAILABLE = True
            logger.info(f" GPU DETECTED via PyTorch: {GPU_DEVICE_NAME}")
            return True
    except ImportError:
        pass
    
    # Check via TensorFlow
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            GPU_DEVICE_NAME = gpus[0].name
            GPU_AVAILABLE = True
            logger.info(f" GPU DETECTED via TensorFlow: {len(gpus)} GPU(s)")
            return True
    except ImportError:
        pass
    
    logger.info(" CPU MODE: No GPU detected")
    GPU_AVAILABLE = False
    return False


def get_gpu_params_autogluon():
    """
    Get GPU configuration parameters for AutoGluon.
    
    Returns:
        dict: Parameters to pass to AutoGluon predictor
    """
    return {}


def get_gpu_params_xgboost():
    """
    Get GPU configuration parameters for XGBoost.
    
    Returns:
        dict: Parameters to pass to XGBoost
    """
    if GPU_AVAILABLE:
        return {
            'tree_method': 'gpu_hist',
            'gpu_id': 0,
            'predictor': 'gpu_predictor',
        }
    return {
        'tree_method': 'hist',  # CPU optimized
    }


def get_gpu_params_lightgbm():
    """
    Get GPU configuration parameters for LightGBM.
    
    Returns:
        dict: Parameters to pass to LightGBM
    """
    if GPU_AVAILABLE:
        return {
            'device': 'gpu',
            'gpu_platform_id': 0,
            'gpu_device_id': 0,
        }
    return {
        'device': 'cpu',
    }


def get_gpu_params_pytorch():
    """
    Get GPU device for PyTorch.
    
    Returns:
        str: 'cuda' if GPU available, else 'cpu'
    """
    if GPU_AVAILABLE:
        return 'cuda'
    return 'cpu'


def get_device_info():
    """
    Get detailed information about available compute devices.
    
    Returns:
        dict: Device information
    """
    info = {
        'gpu_available': GPU_AVAILABLE,
        'device_name': GPU_DEVICE_NAME,
        'device_type': 'GPU' if GPU_AVAILABLE else 'CPU',
    }
    
    # Add PyTorch info
    try:
        import torch
        info['pytorch_device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        if torch.cuda.is_available():
            info['pytorch_gpu_count'] = torch.cuda.device_count()
            info['pytorch_gpu_name'] = torch.cuda.get_device_name(0)
            info['pytorch_cuda_version'] = torch.version.cuda
    except ImportError:
        pass
    
    # Add TensorFlow info
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        info['tensorflow_gpu_count'] = len(gpus)
    except ImportError:
        pass
    
    return info


def print_gpu_status():
    """
    Print GPU status to console.
    """
    info = get_device_info()
    print("\n" + "="*60)
    print("  COMPUTE DEVICE STATUS")
    print("="*60)
    print(f"Device Type: {info['device_type']}")
    if info['gpu_available']:
        print(f"GPU Name: {info['device_name']}")
        if 'pytorch_cuda_version' in info:
            print(f"CUDA Version: {info['pytorch_cuda_version']}")
        if 'pytorch_gpu_count' in info:
            print(f"PyTorch GPUs: {info['pytorch_gpu_count']}")
        if 'tensorflow_gpu_count' in info:
            print(f"TensorFlow GPUs: {info['tensorflow_gpu_count']}")
    print("="*60 + "\n")


# Auto-detect GPU on module import
detect_and_set_gpu()

