#!/usr/bin/env python3
"""
Check all imports in data_science files and verify they're installed.
"""

import os
import re
import ast
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

def extract_imports_from_file(file_path):
    """Extract all import statements from a Python file."""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    
    except Exception as e:
        print(f"[WARNING] Error parsing {file_path}: {e}")
    
    return imports

def get_pip_name(import_name):
    """Map Python import names to pip package names."""
    mapping = {
        # Standard library (skip these)
        'os': None,
        'sys': None,
        'io': None,
        'json': None,
        'logging': None,
        'typing': None,
        'datetime': None,
        'time': None,
        'random': None,
        'asyncio': None,
        'glob': None,
        'importlib': None,
        'inspect': None,
        'functools': None,
        'pathlib': None,
        'subprocess': None,
        'collections': None,
        're': None,
        'ast': None,
        'warnings': None,
        'signal': None,
        
        # Google/ADK packages
        'google': None,  # Comes with ADK
        
        # Common mappings
        'cv2': 'opencv-python',
        'sklearn': 'scikit-learn',
        'dotenv': 'python-dotenv',
        'imblearn': 'imbalanced-learn',
        'sentence_transformers': 'sentence-transformers',
        'alibi_detect': 'alibi-detect',
        'faiss': 'faiss-cpu',  # or faiss-gpu
        'great_expectations': 'great-expectations',
        'cupy': 'cupy-cuda12x',
        
        # Direct mappings (import name == pip name)
        'pandas': 'pandas',
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'joblib': 'joblib',
        'scipy': 'scipy',
        'statsmodels': 'statsmodels',
        'litellm': 'litellm',
        'openai': 'openai',
        'uvicorn': 'uvicorn',
        'fastapi': 'fastapi',
        'optuna': 'optuna',
        'mlflow': 'mlflow',
        'fairlearn': 'fairlearn',
        'evidently': 'evidently',
        'dowhy': 'dowhy',
        'featuretools': 'featuretools',
        'prophet': 'prophet',
        'dvc': 'dvc',
        'duckdb': 'duckdb',
        'polars': 'polars',
        'torch': 'torch',
        'xgboost': 'xgboost',
        'lightgbm': 'lightgbm',
        'autogluon': 'autogluon',
        'PIL': 'pillow',
        'reportlab': 'reportlab',
        'shap': 'shap',
        'econml': 'econml',
        'tqdm': 'tqdm',
        'boto3': 'boto3',
        'pydantic': 'pydantic',
        'requests': 'requests',
        'aiohttp': 'aiohttp',
        'httpx': 'httpx',
    }
    
    return mapping.get(import_name, import_name)

def main():
    print("=" * 70)
    print("CHECKING ALL IMPORTS IN DATA SCIENCE FILES")
    print("=" * 70)
    print()
    
    # Find all Python files in data_science directory
    data_science_dir = Path('data_science')
    all_imports = set()
    file_imports = {}
    
    for py_file in data_science_dir.glob('*.py'):
        if py_file.name == '__pycache__':
            continue
        
        imports = extract_imports_from_file(py_file)
        file_imports[py_file.name] = imports
        all_imports.update(imports)
    
    print(f"[INFO] Found {len(all_imports)} unique imports across {len(file_imports)} files\n")
    
    # Map to pip packages
    pip_packages = {}
    standard_lib = []
    
    for imp in sorted(all_imports):
        pip_name = get_pip_name(imp)
        if pip_name is None:
            standard_lib.append(imp)
        else:
            pip_packages[imp] = pip_name
    
    print(f"[OK] Standard library imports (skip): {len(standard_lib)}")
    print(f"[INFO] Third-party packages needed: {len(pip_packages)}\n")
    
    # Check requirements.txt
    requirements_file = Path('requirements.txt')
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            requirements_content = f.read().lower()
    else:
        requirements_content = ""
    
    # Check which packages are missing
    missing_in_requirements = []
    present_in_requirements = []
    
    for imp, pip_name in sorted(pip_packages.items()):
        # Check if package name appears in requirements
        if pip_name.lower() in requirements_content or pip_name.split('[')[0].lower() in requirements_content:
            present_in_requirements.append((imp, pip_name))
        else:
            missing_in_requirements.append((imp, pip_name))
    
    # Report results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    if present_in_requirements:
        print(f"[OK] FOUND IN requirements.txt ({len(present_in_requirements)}):")
        for imp, pip_name in present_in_requirements:
            print(f"   [+] {imp:30} -> {pip_name}")
        print()
    
    if missing_in_requirements:
        print(f"[MISSING] NOT IN requirements.txt ({len(missing_in_requirements)}):")
        for imp, pip_name in missing_in_requirements:
            print(f"   [-] {imp:30} -> {pip_name}")
        print()
        
        print("=" * 70)
        print("ADD THESE TO requirements.txt:")
        print("=" * 70)
        for imp, pip_name in missing_in_requirements:
            print(pip_name)
    else:
        print("[SUCCESS] ALL PACKAGES ARE IN requirements.txt!")
    
    print()
    print("=" * 70)
    print("STANDARD LIBRARY IMPORTS (no installation needed):")
    print("=" * 70)
    for imp in sorted(standard_lib):
        print(f"   {imp}")
    
    # Show which files use which packages
    print()
    print("=" * 70)
    print("PACKAGE USAGE BY FILE:")
    print("=" * 70)
    for file_name, imports in sorted(file_imports.items()):
        third_party = [imp for imp in imports if get_pip_name(imp) is not None]
        if third_party:
            print(f"\n{file_name}:")
            for imp in sorted(third_party):
                pip_name = get_pip_name(imp)
                print(f"   * {imp:25} -> {pip_name}")

if __name__ == '__main__':
    main()

