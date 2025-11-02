# 📁 Real-Time Workspace Folder Monitor
# Watches for new files being created in workspace folders

param(
    [string]$WorkspacePath = "C:\harfile\data_science_agent\data_science\.uploaded\_workspaces",
    [switch]$ShowExisting = $false
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "📁 WORKSPACE FOLDER MONITOR" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Watching: $WorkspacePath" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Gray
Write-Host ""

# Find the most recent workspace
$latestWorkspace = Get-ChildItem -Path $WorkspacePath -Directory -Recurse -Filter "202*" -ErrorAction SilentlyContinue | 
    Where-Object { $_.Name -match '^\d{8}_\d{6}$' } |
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1

if ($latestWorkspace) {
    $watchPath = $latestWorkspace.FullName
    Write-Host "✓ Found latest workspace: $($latestWorkspace.Name)" -ForegroundColor Green
    Write-Host "  Full path: $watchPath" -ForegroundColor Gray
} else {
    $watchPath = $WorkspacePath
    Write-Host "⚠ No timestamped workspace found, watching root: $watchPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Show existing files if requested
if ($ShowExisting) {
    Write-Host "📋 EXISTING FILES:" -ForegroundColor Cyan
    $folders = @("reports", "results", "plots", "models", "data", "uploads")
    foreach ($folder in $folders) {
        $folderPath = Join-Path $watchPath $folder
        if (Test-Path $folderPath) {
            $files = Get-ChildItem -Path $folderPath -File -ErrorAction SilentlyContinue
            if ($files.Count -gt 0) {
                Write-Host "  📁 $folder/ ($($files.Count) files)" -ForegroundColor Yellow
                foreach ($file in $files | Select-Object -First 5) {
                    $size = if ($file.Length -lt 1KB) { "$($file.Length) B" } 
                           elseif ($file.Length -lt 1MB) { "{0:N2} KB" -f ($file.Length / 1KB) }
                           else { "{0:N2} MB" -f ($file.Length / 1MB) }
                    Write-Host "    - $($file.Name) ($size)" -ForegroundColor Gray
                }
                if ($files.Count -gt 5) {
                    Write-Host "    ... and $($files.Count - 5) more" -ForegroundColor DarkGray
                }
            }
        }
    }
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

# Create FileSystemWatcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# Define what to watch
$watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName -bor 
                        [System.IO.NotifyFilters]::LastWrite -bor
                        [System.IO.NotifyFilters]::CreationTime

# Define the action when a file is created
$actionCreated = {
    $path = $Event.SourceEventArgs.FullPath
    $name = $Event.SourceEventArgs.Name
    $changeType = $Event.SourceEventArgs.ChangeType
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    # Get file size
    try {
        $file = Get-Item $path -ErrorAction SilentlyContinue
        if ($file) {
            $size = if ($file.Length -lt 1KB) { "$($file.Length) B" } 
                   elseif ($file.Length -lt 1MB) { "{0:N2} KB" -f ($file.Length / 1KB) }
                   else { "{0:N2} MB" -f ($file.Length / 1MB) }
            
            # Determine folder type
            $folder = Split-Path (Split-Path $path -Parent) -Leaf
            $icon = switch ($folder) {
                "reports"   { "📄" }
                "results"   { "📊" }
                "plots"     { "📈" }
                "models"    { "🤖" }
                "data"      { "💾" }
                "uploads"   { "📥" }
                "metrics"   { "📏" }
                "logs"      { "📝" }
                default     { "📁" }
            }
            
            $color = switch ($folder) {
                "reports"   { "Green" }
                "results"   { "Cyan" }
                "plots"     { "Magenta" }
                "models"    { "Yellow" }
                default     { "White" }
            }
            
            Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
            Write-Host "$icon $changeType: " -NoNewline -ForegroundColor $color
            Write-Host "$folder/" -NoNewline -ForegroundColor DarkGray
            Write-Host "$($file.Name) " -NoNewline -ForegroundColor $color
            Write-Host "($size)" -ForegroundColor Gray
        }
    } catch {
        # File might be locked or deleted immediately
    }
}

# Define the action when a file is modified
$actionModified = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    try {
        $file = Get-Item $path -ErrorAction SilentlyContinue
        if ($file -and $file.Length -gt 0) {
            $folder = Split-Path (Split-Path $path -Parent) -Leaf
            $size = if ($file.Length -lt 1KB) { "$($file.Length) B" } 
                   elseif ($file.Length -lt 1MB) { "{0:N2} KB" -f ($file.Length / 1KB) }
                   else { "{0:N2} MB" -f ($file.Length / 1MB) }
            
            Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
            Write-Host "✏️  $changeType: " -NoNewline -ForegroundColor Yellow
            Write-Host "$folder/" -NoNewline -ForegroundColor DarkGray
            Write-Host "$($file.Name) " -NoNewline -ForegroundColor White
            Write-Host "($size)" -ForegroundColor Gray
        }
    } catch {
        # Ignore
    }
}

# Register events
$handlers = @()
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $actionCreated
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $actionModified

Write-Host "👁️  WATCHING FOR NEW FILES..." -ForegroundColor Green
Write-Host "(Run a tool to see artifacts being created)" -ForegroundColor Gray
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    # Cleanup
    Write-Host ""
    Write-Host "Stopping monitor..." -ForegroundColor Yellow
    $handlers | ForEach-Object { Unregister-Event -SourceIdentifier $_.Name }
    $watcher.Dispose()
    Write-Host "Monitor stopped." -ForegroundColor Gray
}

