# 📁 Folder Monitoring Guide

## Quick Start - Watch Folders in Real-Time

### Option 1: PowerShell Watcher (Recommended)

```powershell
# Navigate to directory
cd C:\harfile\data_science_agent\data_science

# Run the watcher
.\watch_folders.ps1

# Or with existing files shown first:
.\watch_folders.ps1 -ShowExisting
```

**What you'll see:**
```
============================================
📁 WORKSPACE FOLDER MONITOR
============================================

Watching: C:\harfile\data_science_agent\data_science\.uploaded\_workspaces
✓ Found latest workspace: 20251101_141642

============================================

👁️  WATCHING FOR NEW FILES...
(Run a tool to see artifacts being created)

[15:05:30] 📄 Created: reports/20251101_150530_123456_analyze_dataset_tool.md (45.23 KB)
[15:05:30] 📊 Created: results/analyze_dataset_tool_output.json (12.45 KB)
[15:05:45] 📈 Created: plots/correlation_plot.png (156.78 KB)
[15:05:45] 📄 Created: reports/20251101_150545_234567_plot_tool.md (23.45 KB)
[15:05:45] 📊 Created: results/plot_tool_output.json (5.67 KB)
```

---

### Option 2: Manual File Listing

```powershell
# Find latest workspace
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces
$latest = Get-ChildItem -Directory -Recurse -Filter "202*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
cd $latest.FullName

# Watch reports folder
Get-ChildItem reports\ -File | Sort-Object LastWriteTime -Descending | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

# Watch results folder
Get-ChildItem results\ -File | Sort-Object LastWriteTime -Descending | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

# Watch plots folder
Get-ChildItem plots\ -File | Sort-Object LastWriteTime -Descending | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize

# Refresh every 2 seconds (run in loop)
while ($true) {
    Clear-Host
    Write-Host "=== REPORTS ===" -ForegroundColor Cyan
    Get-ChildItem reports\ -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, Length, LastWriteTime -AutoSize
    Write-Host "`n=== RESULTS ===" -ForegroundColor Cyan
    Get-ChildItem results\ -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, Length, LastWriteTime -AutoSize
    Start-Sleep -Seconds 2
}
```

---

### Option 3: Simple Count Watcher

```powershell
# Watch file counts in real-time
while ($true) {
    $reports = (Get-ChildItem C:\harfile\data_science_agent\data_science\.uploaded\_workspaces -Recurse -Filter *.md -File -ErrorAction SilentlyContinue).Count
    $results = (Get-ChildItem C:\harfile\data_science_agent\data_science\.uploaded\_workspaces -Recurse -Filter *.json -File -ErrorAction SilentlyContinue).Count
    $plots = (Get-ChildItem C:\harfile\data_science_agent\data_science\.uploaded\_workspaces -Recurse -Filter *.png -File -ErrorAction SilentlyContinue).Count
    
    Clear-Host
    Write-Host "📁 WORKSPACE FILE COUNTS" -ForegroundColor Yellow
    Write-Host "=========================" -ForegroundColor Yellow
    Write-Host "📄 Markdown (reports): $reports" -ForegroundColor Green
    Write-Host "📊 JSON (results): $results" -ForegroundColor Cyan
    Write-Host "📈 Plots: $plots" -ForegroundColor Magenta
    Write-Host "`nRefreshing every 2 seconds... (Ctrl+C to stop)" -ForegroundColor Gray
    
    Start-Sleep -Seconds 2
}
```

---

## Testing Workflow

### Terminal 1: Start Server
```bash
cd C:\harfile\data_science_agent
python -m data_science.main
```

### Terminal 2: Watch Folders
```powershell
cd C:\harfile\data_science_agent\data_science
.\watch_folders.ps1 -ShowExisting
```

### Terminal 3: Test Commands
```
1. Upload CSV file
2. Run: analyze_dataset_tool()
3. Watch Terminal 2 for file creation
```

---

## Expected Output Pattern

### After File Upload:
```
[15:05:00] 📥 Created: uploads/healthexp.csv (1.23 MB)
```

### After analyze_dataset_tool():
```
[15:05:30] 📄 Created: reports/20251101_150530_123456_analyze_dataset_tool.md (45.23 KB)
[15:05:30] 📊 Created: results/analyze_dataset_tool_output.json (12.45 KB)
```

### After describe_tool_guard():
```
[15:05:45] 📄 Created: reports/20251101_150545_234567_describe_tool_guard.md (23.45 KB)
[15:05:45] 📊 Created: results/describe_tool_guard_output.json (5.67 KB)
```

### After plot_tool():
```
[15:06:00] 📈 Created: plots/correlation_plot.png (156.78 KB)
[15:06:00] 📄 Created: reports/20251101_150600_345678_plot_tool.md (18.92 KB)
[15:06:00] 📊 Created: results/plot_tool_output.json (4.56 KB)
```

### After train_classifier():
```
[15:06:15] 🤖 Created: models/random_forest_classifier.pkl (2.34 MB)
[15:06:15] 📄 Created: reports/20251101_150615_456789_train_classifier.md (67.89 KB)
[15:06:15] 📊 Created: results/train_classifier_output.json (15.67 KB)
```

---

## Folder Legend

| Icon | Folder | File Types | Purpose |
|------|--------|------------|---------|
| 📄 | `reports/` | `.md` | Human-readable documentation |
| 📊 | `results/` | `.json` | Machine-readable structured data |
| 📈 | `plots/` | `.png`, `.jpg`, `.svg` | Visualizations and charts |
| 🤖 | `models/` | `.pkl`, `.joblib` | Trained ML models |
| 💾 | `data/` | `.csv`, `.parquet` | Processed datasets |
| 📥 | `uploads/` | `.csv`, `.xlsx` | Original uploaded files |
| 📏 | `metrics/` | `.json` | Model evaluation metrics |
| 📝 | `logs/` | `.log` | Debug and execution logs |

---

## Troubleshooting

### No Files Appearing?

1. **Check workspace path:**
```powershell
Get-ChildItem C:\harfile\data_science_agent\data_science\.uploaded\_workspaces -Recurse -Directory | 
    Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 | 
    Format-List FullName
```

2. **Check if folders exist:**
```powershell
$workspace = "C:\harfile\data_science_agent\data_science\.uploaded\_workspaces\healthexp\20251101_141642"
Get-ChildItem $workspace -Directory | Select-Object Name
```

3. **Check server logs:**
```bash
# Look for:
[MARKDOWN ARTIFACT] ✅✅✅ FILESYSTEM SAVE SUCCESS
[JSON ARTIFACT] ✅ Saved to filesystem
```

---

## Quick Verification

### After running ANY tool:

```powershell
# Count total artifacts
$workspace = Get-ChildItem C:\harfile\data_science_agent\data_science\.uploaded\_workspaces -Recurse -Directory -Filter "202*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "📁 Workspace: $($workspace.Name)" -ForegroundColor Yellow
Write-Host "📄 Reports: $((Get-ChildItem "$($workspace.FullName)\reports" -File -ErrorAction SilentlyContinue).Count)" -ForegroundColor Green
Write-Host "📊 Results: $((Get-ChildItem "$($workspace.FullName)\results" -File -ErrorAction SilentlyContinue).Count)" -ForegroundColor Cyan
Write-Host "📈 Plots: $((Get-ChildItem "$($workspace.FullName)\plots" -File -ErrorAction SilentlyContinue).Count)" -ForegroundColor Magenta
```

Expected output (after 3 tools):
```
📁 Workspace: 20251101_141642
📄 Reports: 3     ← 1 per tool
📊 Results: 3     ← 1 per tool
📈 Plots: 1       ← If plot tool was used
```

---

## Stop Watching

Press **Ctrl+C** in the monitoring terminal to stop the watcher.

---

## Summary

✅ **Use `watch_folders.ps1`** for real-time monitoring
✅ **See files as they're created** with timestamps and sizes
✅ **Verify 100% coverage** - every tool creates files
✅ **Color-coded output** for easy identification
✅ **No manual refresh needed** - automatic detection

**Start watching now and run some tools!** 🚀

