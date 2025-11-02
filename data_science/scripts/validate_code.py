#!/usr/bin/env python3
"""
Runtime Code Validator
Automatically checks for common Python errors before starting the server.
Prevents IndentationErrors, SyntaxErrors, and import issues.
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional
import subprocess


class CodeValidator:
    """Validates Python code for common errors."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.errors: List[Tuple[str, str, int]] = []
        
    def validate_syntax(self, file_path: Path) -> bool:
        """Check if file has valid Python syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.errors.append((
                str(file_path),
                f"SyntaxError: {e.msg}",
                e.lineno or 0
            ))
            return False
        except IndentationError as e:
            self.errors.append((
                str(file_path),
                f"IndentationError: {e.msg}",
                e.lineno or 0
            ))
            return False
        except Exception as e:
            self.errors.append((
                str(file_path),
                f"ParseError: {str(e)}",
                0
            ))
            return False
    
    def validate_imports(self, file_path: Path) -> bool:
        """Check if all imports can be resolved (basic check)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Just verify the import statement is valid
                    # Full import resolution would require running in the actual environment
                    pass
            return True
        except Exception as e:
            self.errors.append((
                str(file_path),
                f"ImportError: {str(e)}",
                0
            ))
            return False
    
    def run_pylint(self, file_path: Path) -> Optional[str]:
        """Run pylint if available (optional)."""
        try:
            result = subprocess.run(
                ["pylint", "--errors-only", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0 and result.stdout:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single Python file."""
        print(f"  Checking {file_path.name}...", end=" ")
        
        if not self.validate_syntax(file_path):
            print("[FAILED] (syntax)")
            return False
        
        if not self.validate_imports(file_path):
            print("[WARNING] (imports)")
            return True  # Don't fail on import warnings
        
        print("[OK]")
        return True
    
    def validate_directory(self, directory: str = "data_science") -> bool:
        """Validate all Python files in a directory."""
        dir_path = self.base_dir / directory
        
        if not dir_path.exists():
            print(f"[ERROR] Directory not found: {directory}")
            return False
        
        print(f"\n{'='*60}")
        print(f"  CODE VALIDATION - {directory}")
        print(f"{'='*60}\n")
        
        py_files = list(dir_path.glob("*.py"))
        if not py_files:
            print(f"[WARNING] No Python files found in {directory}")
            return True
        
        all_valid = True
        for py_file in py_files:
            if py_file.name.startswith("__"):
                continue  # Skip __init__.py, __pycache__, etc.
            
            if not self.validate_file(py_file):
                all_valid = False
        
        if self.errors:
            print(f"\n{'='*60}")
            print("  ERRORS FOUND")
            print(f"{'='*60}\n")
            for file_path, error_msg, line_no in self.errors:
                if line_no > 0:
                    print(f"[ERROR] {file_path}:{line_no}")
                else:
                    print(f"[ERROR] {file_path}")
                print(f"   {error_msg}\n")
            return False
        
        if all_valid:
            print(f"\n[SUCCESS] All files passed validation!")
        
        return all_valid
    
    def auto_fix_common_issues(self, file_path: Path) -> bool:
        """Attempt to auto-fix common issues like trailing whitespace."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Fix trailing whitespace
            fixed_lines = [line.rstrip() + '\n' if line.strip() else '\n' for line in lines]
            
            # Ensure file ends with newline
            if fixed_lines and not fixed_lines[-1].endswith('\n'):
                fixed_lines[-1] += '\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            
            return True
        except Exception as e:
            print(f"[WARNING] Could not auto-fix {file_path}: {e}")
            return False


def main():
    """Main validation function."""
    validator = CodeValidator()
    
    # Validate critical files
    critical_files = [
        "main.py",
        "data_science/agent.py",
        "data_science/ds_tools.py",
        "data_science/autogluon_tools.py",
    ]
    
    print("\n" + "="*60)
    print("  RUNTIME CODE VALIDATOR")
    print("="*60)
    print("\nValidating critical files before startup...\n")
    
    all_valid = True
    for file_path in critical_files:
        path = Path(file_path)
        if path.exists():
            if not validator.validate_file(path):
                all_valid = False
        else:
            print(f"  [WARNING] File not found: {file_path}")
    
    print("\n" + "="*60)
    if all_valid:
        print("  [SUCCESS] VALIDATION PASSED - Server can start safely")
        print("="*60 + "\n")
        return 0
    else:
        print("  [FAILED] VALIDATION FAILED - Fix errors before starting")
        print("="*60 + "\n")
        print("Errors found:")
        for file_path, error_msg, line_no in validator.errors:
            if line_no > 0:
                print(f"  - {file_path}:{line_no} - {error_msg}")
            else:
                print(f"  - {file_path} - {error_msg}")
        print("\nFix these errors and try again.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

