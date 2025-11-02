# Start Data Science Agent with Runtime Validation
# This script validates code for syntax errors before starting the server

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  DATA SCIENCE AGENT - SAFE STARTUP" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Run code validation
Write-Host "Step 1: Running code validation..." -ForegroundColor Yellow
Write-Host ""

$validation = uv run python validate_code.py
$validationExit = $LASTEXITCODE

if ($validationExit -ne 0) {
    Write-Host ""
    Write-Host "❌ CODE VALIDATION FAILED!" -ForegroundColor Red
    Write-Host "Cannot start server with syntax errors." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this to see details:" -ForegroundColor Yellow
    Write-Host "  uv run python validate_code.py" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "✅ Code validation passed!" -ForegroundColor Green
Write-Host ""

# Step 2: Set environment variables
Write-Host "Step 2: Setting environment variables..." -ForegroundColor Yellow
$env:SERVE_WEB_INTERFACE = 'true'
$env:LOG_LEVEL = 'DEBUG'
Write-Host "  ✓ SERVE_WEB_INTERFACE = true" -ForegroundColor Green
Write-Host "  ✓ LOG_LEVEL = DEBUG" -ForegroundColor Green
Write-Host ""

# Step 3: Check OpenAI API key
Write-Host "Step 3: Checking OpenAI API key..." -ForegroundColor Yellow
if ($env:OPENAI_API_KEY) {
    $keyPreview = $env:OPENAI_API_KEY.Substring(0, [Math]::Min(10, $env:OPENAI_API_KEY.Length)) + "..."
    Write-Host "  ✓ API Key found: $keyPreview" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  OPENAI_API_KEY not set" -ForegroundColor Yellow
    Write-Host "  Set it with: `$env:OPENAI_API_KEY='your-key-here'" -ForegroundColor White
}
Write-Host ""

# Step 4: Start server
Write-Host "Step 4: Starting ADK server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SERVER STARTING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Start the server
uv run python main.py

# If we get here, server stopped
Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow

