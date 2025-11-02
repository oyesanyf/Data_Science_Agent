# Clear Python bytecode cache to fix ToolContext import issue

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Clearing Python Bytecode Cache" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location -Path "C:\harfile\data_science_agent"

# Count __pycache__ directories before deletion
$pycacheDirs = Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory -Force
$count = ($pycacheDirs | Measure-Object).Count

if ($count -eq 0) {
    Write-Host "No __pycache__ directories found." -ForegroundColor Green
} else {
    Write-Host "Found $count __pycache__ directories to remove..." -ForegroundColor Yellow
    
    # Remove all __pycache__ directories
    Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory -Force | Remove-Item -Recurse -Force
    
    Write-Host "✅ Cleared $count __pycache__ directories!" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Cache cleared! Now restart the server:" -ForegroundColor Cyan
Write-Host "  python start_server.py" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

