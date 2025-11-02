# 🧹 Clean Up Old/Broken Workspace Folders
# This script removes legacy workspace folders created by old buggy code

param(
    [switch]$DryRun = $true,  # Default: just show what would be deleted
    [switch]$Force = $false    # Actually delete (use with caution!)
)

$WorkspacesRoot = "C:\harfile\data_science_agent\data_science\.uploaded\_workspaces"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🧹 WORKSPACE CLEANUP UTILITY" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "⚠️  DRY RUN MODE (no changes will be made)" -ForegroundColor Yellow
    Write-Host "   Run with -Force to actually delete folders" -ForegroundColor Gray
} else {
    Write-Host "🚨 DELETION MODE ACTIVE" -ForegroundColor Red
    Write-Host "   Folders will be permanently deleted!" -ForegroundColor Red
}
Write-Host ""

# Get all top-level folders
$allFolders = Get-ChildItem -Path $WorkspacesRoot -Directory

Write-Host "📊 ANALYSIS:" -ForegroundColor Cyan
Write-Host ""

# Categorize folders
$goodFolders = @()
$badFolders = @()

foreach ($folder in $allFolders) {
    $name = $folder.Name
    $path = $folder.FullName
    
    # Check if folder contains timestamp subfolders (good pattern)
    $hasTimestampSubfolders = (Get-ChildItem -Path $path -Directory -Filter "202*" -ErrorAction SilentlyContinue | 
        Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | 
        Measure-Object).Count -gt 0
    
    # Check if folder name has bad patterns
    $hasBadPattern = $name -match '_[0-9a-f]{8}$' -or   # Hash suffix
                     $name -match '_utf8_' -or           # UTF8 hash pattern
                     $name -eq 'default' -or             # Generic name
                     $name -eq '_global' -or             # Generic name
                     $name -eq 'uploaded'                # Old "uploaded" without run_ids (but check contents)
    
    # Special case: "uploaded" is good if it has timestamp subfolders
    if ($name -eq 'uploaded' -and $hasTimestampSubfolders) {
        $hasBadPattern = $false
    }
    
    if ($hasTimestampSubfolders -and -not $hasBadPattern) {
        $goodFolders += $folder
    } else {
        $badFolders += $folder
    }
}

Write-Host "✅ GOOD FOLDERS (will be kept):" -ForegroundColor Green
Write-Host ""
if ($goodFolders.Count -eq 0) {
    Write-Host "   (none found)" -ForegroundColor Gray
} else {
    foreach ($folder in $goodFolders | Sort-Object Name) {
        $subfolders = Get-ChildItem -Path $folder.FullName -Directory -Filter "202*" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^\d{8}_\d{6}$' } |
            Measure-Object
        Write-Host "   ✓ $($folder.Name)/" -ForegroundColor Green -NoNewline
        Write-Host " (contains $($subfolders.Count) run folder(s))" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "❌ BAD FOLDERS (will be deleted):" -ForegroundColor Red
Write-Host ""
if ($badFolders.Count -eq 0) {
    Write-Host "   (none found - workspace is clean!)" -ForegroundColor Green
} else {
    $totalSize = 0
    foreach ($folder in $badFolders | Sort-Object Name) {
        try {
            $size = (Get-ChildItem -Path $folder.FullName -Recurse -File -ErrorAction SilentlyContinue | 
                Measure-Object -Property Length -Sum).Sum
            $sizeStr = if ($size -lt 1KB) { "$size B" }
                      elseif ($size -lt 1MB) { "{0:N2} KB" -f ($size / 1KB) }
                      else { "{0:N2} MB" -f ($size / 1MB) }
            $totalSize += $size
            Write-Host "   ✗ $($folder.Name)/" -ForegroundColor Red -NoNewline
            Write-Host " ($sizeStr, created $($folder.CreationTime))" -ForegroundColor Gray
        } catch {
            Write-Host "   ✗ $($folder.Name)/" -ForegroundColor Red -NoNewline
            Write-Host " (size unknown)" -ForegroundColor Gray
        }
    }
    Write-Host ""
    $totalSizeStr = if ($totalSize -lt 1KB) { "$totalSize B" }
                   elseif ($totalSize -lt 1MB) { "{0:N2} KB" -f ($totalSize / 1KB) }
                   else { "{0:N2} MB" -f ($totalSize / 1MB) }
    Write-Host "   Total size to delete: $totalSizeStr" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Perform deletion if Force flag is set
if (-not $DryRun -and $Force -and $badFolders.Count -gt 0) {
    Write-Host "🗑️  DELETING BAD FOLDERS..." -ForegroundColor Red
    Write-Host ""
    
    foreach ($folder in $badFolders) {
        try {
            Write-Host "   Deleting: $($folder.Name)... " -NoNewline -ForegroundColor Yellow
            Remove-Item -Path $folder.FullName -Recurse -Force -ErrorAction Stop
            Write-Host "✓ Done" -ForegroundColor Green
        } catch {
            Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "✅ Cleanup complete!" -ForegroundColor Green
} elseif ($badFolders.Count -gt 0) {
    Write-Host "💡 TO DELETE THESE FOLDERS:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Run: .\cleanup_old_workspaces.ps1 -DryRun:`$false -Force" -ForegroundColor White
    Write-Host ""
    Write-Host "   Or manually delete:" -ForegroundColor Gray
    foreach ($folder in $badFolders | Select-Object -First 3) {
        Write-Host "   Remove-Item ""$($folder.FullName)"" -Recurse -Force" -ForegroundColor DarkGray
    }
    if ($badFolders.Count -gt 3) {
        Write-Host "   ... and $($badFolders.Count - 3) more" -ForegroundColor DarkGray
    }
} else {
    Write-Host "✅ Workspace is clean - no bad folders to delete!" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

