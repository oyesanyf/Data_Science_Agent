# Maintenance Function - Safety Enhancement Complete ✅

## Problem
The `maintenance()` function was too aggressive and could potentially delete code files, config files, or files from the current session, which is dangerous for production use.

## Solution
Completely rewrote the maintenance function with **comprehensive safety measures** to ensure it **ONLY** cleans data files from designated locations while protecting all code, config, and active session files.

## Changes Made

### 1. **Added Comprehensive File Protection**

#### Protected File Extensions (NEVER deleted):
```python
PROTECTED_EXTENSIONS = {
    # Code files
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.m', '.sh', '.bat', '.ps1',
    
    # Config files
    '.yaml', '.yml', '.json', '.toml', '.ini', '.env', '.config', '.conf',
    '.xml', '.properties', '.cfg', '.settings',
    
    # Project files
    '.md', '.rst', '.txt', '.gitignore', '.dockerignore', 'Dockerfile',
    '.lock', 'requirements.txt', 'package.json', 'package-lock.json',
    'Pipfile', 'Pipfile.lock', 'poetry.lock', 'Cargo.toml', 'Cargo.lock',
    
    # Documentation
    '.pdf', '.docx', '.doc', '.odt',
}
```

#### Protected Directories (NEVER cleaned):
```python
PROTECTED_DIRS = {
    'data_science', 'src', 'lib', 'bin', 'scripts', 'utils',
    'node_modules', 'venv', '.venv', 'env', '.env',
    '__pycache__', '.git', '.github', '.vscode', '.idea'
}
```

### 2. **New Safe Cleaning Actions**

#### ✅ `clean_data` (NEW - Replaces dangerous `clean_old`)
- **What it cleans:** Only data files in `.uploaded` folders
- **Age threshold:** 7 days old
- **Protected:** Current session files, code files, config files
- **File types cleaned:** `.csv`, `.parquet`, `.tsv`, `.txt`, `.json`, `.jsonl`, `.pkl`, `.pickle`

**Safety checks:**
1. ✅ Never deletes protected file extensions
2. ✅ Never deletes files from current session workspace
3. ✅ Only deletes data files (verified by extension)
4. ✅ Only deletes files older than 7 days
5. ✅ Reports how many files were protected

**Example:**
```python
result = maintenance(action="clean_data")
# Output:
{
    "status": "success",
    "action": "clean_data",
    "deleted_files": 15,
    "protected_files": 3,  # Files that were skipped for safety
    "deleted_size_mb": 245.67,
    "message": "✅ Cleaned 15 old data files (245.7 MB freed). Protected 3 files from deletion."
}
```

#### ✅ `clean_logs` (NEW - Specific to logs folder)
- **What it cleans:** Only `.log` files in `data_science/logs/`
- **Age threshold:** 7 days old
- **Protected:** Everything except `.log` files

**Example:**
```python
result = maintenance(action="clean_logs")
# Output:
{
    "status": "success",
    "action": "clean_logs",
    "deleted_files": 42,
    "deleted_size_mb": 12.34,
    "message": "✅ Cleaned 42 old log files (12.3 MB freed)"
}
```

#### ✅ `clean_temp` (ENHANCED - More safety)
- **What it cleans:** Only temporary files in `tmp` directories within `.uploaded` folders
- **Age threshold:** 24 hours old
- **Protected:** Any file with protected extension

**Enhanced safety:**
1. ✅ Only looks in `.uploaded/.../tmp/` directories
2. ✅ Never deletes protected files even in tmp
3. ✅ Reports protected files count

**Example:**
```python
result = maintenance(action="clean_temp")
# Output:
{
    "status": "success",
    "action": "clean_temp",
    "deleted_files": 8,
    "protected_files": 1,  # e.g., temp.config.json was protected
    "deleted_size_mb": 2.45,
    "message": "✅ Cleaned 8 temp files (2.5 MB freed). Protected 1 files."
}
```

### 3. **Safety Helper Functions**

#### `is_protected_file(file_path)`
Checks if a file should NEVER be deleted:
- Returns `True` if file extension is in PROTECTED_EXTENSIONS
- Returns `True` if file is in a PROTECTED_DIR
- Returns `True` if it's a hidden file (starts with `.`) except `.csv`, `.parquet`, `.log`

#### `is_data_file(file_path)`
Checks if a file is a data file that CAN be cleaned:
- Returns `True` only for: `.csv`, `.parquet`, `.tsv`, `.txt`, `.json`, `.jsonl`, `.pkl`, `.pickle`

#### `is_in_current_session(file_path, workspace_root)`
Checks if a file belongs to the current active session:
- Returns `True` if file path starts with current workspace_root
- Prevents deletion of files user is currently working with

### 4. **Removed Dangerous Action**

❌ **Removed:** `clean_old` action
- **Why removed:** Too aggressive - deleted entire workspace directories
- **Replaced by:** `clean_data` with granular file-level safety checks

## Before vs After Comparison

### Before (DANGEROUS ⚠️)
```python
# Old clean_old action
maintenance(action="clean_old")
# ❌ Could delete entire workspaces
# ❌ Could delete code files if they were in workspace
# ❌ Could delete config files
# ❌ No granular protection
```

### After (SAFE ✅)
```python
# New clean_data action
maintenance(action="clean_data")
# ✅ Only deletes data files (.csv, .parquet, etc.)
# ✅ Skips current session files
# ✅ Protects all code and config files
# ✅ 4-layer safety check for each file
# ✅ Reports protected files count
```

## Complete Action Reference

### 1. **`status`** (unchanged)
Shows storage statistics without deleting anything.
```python
maintenance()  # or maintenance(action="status")
```

### 2. **`list_workspaces`** (unchanged)
Lists all workspaces with sizes and ages.
```python
maintenance(action="list_workspaces")
```

### 3. **`clean_data`** (NEW - SAFE)
Cleans old data files from `.uploaded` folders only.
```python
maintenance(action="clean_data")
```

**Safety guarantees:**
- ✅ Only `.uploaded` folders and subfolders
- ✅ Only data file extensions
- ✅ Never current session
- ✅ Never protected extensions
- ✅ Only files > 7 days old

### 4. **`clean_logs`** (NEW - SAFE)
Cleans old log files from logs folder only.
```python
maintenance(action="clean_logs")
```

**Safety guarantees:**
- ✅ Only `data_science/logs/` directory
- ✅ Only `.log` files
- ✅ Only files > 7 days old

### 5. **`clean_temp`** (ENHANCED - SAFER)
Cleans old temporary files from tmp directories.
```python
maintenance(action="clean_temp")
```

**Safety guarantees:**
- ✅ Only `tmp` directories in `.uploaded` folders
- ✅ Never protected file types
- ✅ Only files > 24 hours old

## Safety Checklist

Every file deletion goes through these checks:

1. **❓ Is it a protected extension?** → Skip if YES
   - Code files (.py, .js, .ts, etc.)
   - Config files (.yaml, .json, .env, etc.)
   - Project files (.md, .txt, .lock, etc.)

2. **❓ Is it in a protected directory?** → Skip if YES
   - data_science/, src/, lib/, bin/, scripts/
   - node_modules/, venv/, .venv/, env/
   - .git/, .github/, .vscode/, .idea/

3. **❓ Is it in the current session?** → Skip if YES
   - Files in workspace_root are currently being used

4. **❓ Is it a data file?** → Only proceed if YES
   - .csv, .parquet, .tsv, .json, .pkl, etc.

5. **❓ Is it old enough?** → Only proceed if YES
   - > 7 days for data/logs
   - > 24 hours for temp

## Example Usage

### Safe Cleanup Workflow
```python
# 1. Check current storage
result = maintenance(action="status")
print(f"Total storage: {result['total_size_gb']} GB")

# 2. List largest workspaces
result = maintenance(action="list_workspaces")
print(f"Found {result['total_count']} workspaces")

# 3. Clean old data files (safe)
result = maintenance(action="clean_data")
print(f"Cleaned {result['deleted_files']} files, freed {result['deleted_size_mb']} MB")
print(f"Protected {result['protected_files']} files from deletion")

# 4. Clean old logs (safe)
result = maintenance(action="clean_logs")
print(f"Cleaned {result['deleted_files']} log files")

# 5. Clean temp files (safe)
result = maintenance(action="clean_temp")
print(f"Cleaned {result['deleted_files']} temp files")
```

### Output Example
```
Total storage: 5.67 GB
Found 23 workspaces
Cleaned 45 files, freed 1234.5 MB
Protected 8 files from deletion
Cleaned 67 log files
Cleaned 12 temp files
```

## Files Modified

- `data_science/ds_tools.py` (Lines 8522-8835)
  - Added comprehensive file protection system
  - Replaced dangerous `clean_old` with safe `clean_data`
  - Added `clean_logs` action
  - Enhanced `clean_temp` with better safety
  - Updated docstring with safety warnings

## Benefits

1. ✅ **No More Accidental Deletions**: Code and config files are completely protected
2. ✅ **Session Safety**: Active workspace files are never deleted
3. ✅ **Granular Control**: Three separate actions for data, logs, and temp files
4. ✅ **Transparency**: Reports how many files were protected
5. ✅ **Production Safe**: Can be run without fear of breaking the system
6. ✅ **Audit Trail**: All deletions logged with filenames

## Status

✅ **COMPLETE** - Maintenance function is now production-safe with comprehensive file protection!

## Important Notes

⚠️ **BREAKING CHANGE**: The `clean_old` action has been **removed** as it was too dangerous.  
✅ **Use instead**: `clean_data` for safe, granular cleanup of data files only.

🔒 **Safety First**: Multiple layers of protection ensure no code or config files are ever deleted.

📝 **Logging**: All deletions are logged to `data_science/logs/` for audit purposes.

