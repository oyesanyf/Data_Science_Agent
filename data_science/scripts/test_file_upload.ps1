# Simple File Upload Test for Data Science Agent

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Testing File Upload to ADK Server" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Create a test CSV file
$testCSV = @"
name,age,score
John,25,85
Jane,30,92
Bob,22,78
"@

$testCSV | Out-File -FilePath "test_data.csv" -Encoding UTF8
Write-Host "✓ Created test_data.csv" -ForegroundColor Green

# Convert to base64
$bytes = [System.IO.File]::ReadAllBytes("test_data.csv")
$base64 = [Convert]::ToBase64String($bytes)
Write-Host "✓ Converted to base64 ($($base64.Length) chars)" -ForegroundColor Green

# Create JSON payload
$payload = @{
    app_name = "data_science"
    user_id = "testuser"
    session_id = "test_upload_$(Get-Date -Format 'HHmmss')"
    content = @{
        parts = @(
            @{
                text = "I'm uploading a CSV file for analysis"
            },
            @{
                inline_data = @{
                    mime_type = "text/csv"
                    data = $base64
                }
            }
        )
    }
} | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "Sending upload request to http://127.0.0.1:8080/run ..." -ForegroundColor Yellow
Write-Host ""

# Send request
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8080/run" -Method POST -Body $payload -ContentType "application/json"
    
    Write-Host "✅ UPLOAD SUCCESSFUL!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
} catch {
    Write-Host "❌ UPLOAD FAILED!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Check your console for upload logs" -ForegroundColor Cyan
Write-Host ""

