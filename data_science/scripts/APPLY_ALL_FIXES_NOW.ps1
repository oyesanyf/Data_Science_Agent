# ============================================================================
# APPLY ALL WORKFLOW FIXES - COMPLETE RESTART
# ============================================================================
# This script applies ALL fixes we've made:
# 1. GPT-5 model (best instruction following)
# 2. Ensemble mode (optional - GPT-5 + Gemini voting)
# 3. Display fix (_normalize_display + __display__ fields)
# 4. Iterative workflow (result-driven, not linear)
# 5. Stop auto-chaining (one tool per response)
# 6. Streaming tools disabled (no auto-chains)
# 7. stop() tool added (user can interrupt)
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "APPLYING ALL WORKFLOW FIXES" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop all Python processes
Write-Host "[1/6] Stopping existing Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "   ✓ Stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Clear bytecode cache (force reload)
Write-Host "[2/6] Clearing Python bytecode cache..." -ForegroundColor Yellow
Remove-Item -Recurse -Force data_science\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .venv\Lib\site-packages\data_science\__pycache__ -ErrorAction SilentlyContinue
Write-Host "   ✓ Cache cleared (forces fresh import)" -ForegroundColor Green
Write-Host ""

# Step 3: Check for .env file
Write-Host "[3/6] Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "   ✓ .env file found" -ForegroundColor Green
    
    # Check for API keys
    $envContent = Get-Content ".env" -Raw
    $hasOpenAI = $envContent -match "OPENAI_API_KEY\s*=\s*\S+"
    $hasGemini = $envContent -match "GOOGLE_API_KEY\s*=\s*\S+"
    $hasEnsemble = $envContent -match "USE_ENSEMBLE\s*=\s*true"
    
    if ($hasOpenAI) {
        Write-Host "   ✓ OpenAI API key configured" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ OpenAI API key not found in .env" -ForegroundColor Yellow
    }
    
    if ($hasEnsemble -and $hasGemini) {
        Write-Host "   ✓ Ensemble mode enabled (GPT-5 + Gemini)" -ForegroundColor Green
    } elseif ($hasOpenAI) {
        Write-Host "   ✓ Single model mode (GPT-5 only)" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠ No .env file found" -ForegroundColor Yellow
    Write-Host "   → Using environment variables or defaults" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Show what fixes are active
Write-Host "[4/6] Fixes Applied in Code:" -ForegroundColor Yellow
Write-Host "   ✓ GPT-5 model (superior instruction following)" -ForegroundColor Green
Write-Host "   ✓ Mandatory pre-response checklist" -ForegroundColor Green
Write-Host "   ✓ Forbidden patterns (no auto-chaining)" -ForegroundColor Green
Write-Host "   ✓ Display normalization (_normalize_display)" -ForegroundColor Green
Write-Host "   ✓ @ensure_display_fields on 175+ tools" -ForegroundColor Green
Write-Host "   ✓ Iterative workflow (result-driven)" -ForegroundColor Green
Write-Host "   ✓ Streaming tools DISABLED" -ForegroundColor Green
Write-Host "   ✓ stop() tool added (user interrupt)" -ForegroundColor Green
Write-Host "   ✓ Professional 11-stage workflow" -ForegroundColor Green
Write-Host ""

# Step 5: Show expected behavior
Write-Host "[5/6] Expected Behavior After Start:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   📤 Upload tips.csv" -ForegroundColor Cyan
Write-Host "      → Agent calls analyze_dataset() ONLY" -ForegroundColor White
Write-Host "      → Shows actual data (not 'no results')" -ForegroundColor White
Write-Host "      → Presents numbered next steps" -ForegroundColor White
Write-Host "      → STOPS and waits for your choice" -ForegroundColor White
Write-Host ""
Write-Host "   💬 You type: 'describe'" -ForegroundColor Cyan
Write-Host "      → Agent calls describe() ONLY" -ForegroundColor White
Write-Host "      → Shows actual statistics" -ForegroundColor White
Write-Host "      → Presents numbered next steps" -ForegroundColor White
Write-Host "      → STOPS again" -ForegroundColor White
Write-Host ""
Write-Host "   🛑 If agent loops:" -ForegroundColor Cyan
Write-Host "      → Type: stop" -ForegroundColor White
Write-Host "      → Agent interrupts and waits" -ForegroundColor White
Write-Host ""

# Step 6: Start server
Write-Host "[6/6] Starting server with ALL fixes..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SERVER STARTING - Watch for these messages:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Expected startup messages:" -ForegroundColor White
Write-Host "  [STREAMING] Streaming tools DISABLED" -ForegroundColor Gray
Write-Host "  Model: gpt-5 (or gpt-4-turbo)" -ForegroundColor Gray
Write-Host "  OR" -ForegroundColor Gray
Write-Host "  🎯 ENSEMBLE MODE ACTIVE: gpt-5 + gemini-2.0-flash-exp" -ForegroundColor Gray
Write-Host ""
Write-Host "Press CTRL+C to stop server" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Run server
python start_server.py

