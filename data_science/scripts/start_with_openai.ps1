# Start Data Science Agent with OpenAI
# This script helps you configure and start the agent with OpenAI

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Data Science Agent - OpenAI Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    
    # Prompt for OpenAI API key
    Write-Host ""
    Write-Host "You need an OpenAI API key to continue." -ForegroundColor Yellow
    Write-Host "Get one at: https://platform.openai.com/api-keys" -ForegroundColor Cyan
    Write-Host ""
    
    $apiKey = Read-Host "Enter your OpenAI API key"
    
    if ($apiKey -eq "") {
        Write-Host "Error: API key is required!" -ForegroundColor Red
        exit 1
    }
    
    # Create .env file
    @"
# OpenAI Configuration
OPENAI_API_KEY=$apiKey
OPENAI_MODEL=gpt-4o-mini

# Web Interface
SERVE_WEB_INTERFACE=true
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Host "✓ .env file created successfully!" -ForegroundColor Green
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting server with OpenAI..." -ForegroundColor Yellow
Write-Host ""

# Set environment variable and start server
$env:SERVE_WEB_INTERFACE='true'
uv run python main.py

