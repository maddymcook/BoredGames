# Final project demo: insurance-charges API flow (Step 4).
# Prerequisites: MLflow tracking server + Flask app running.
#
#   mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db
#   $env:FLASK_APP = "data5580_hw.app:create_app"
#   python -m flask run --host 127.0.0.1 --port 5000
#
# Usage:
#   .\scripts\demo_insurance_flow.ps1
#   .\scripts\demo_insurance_flow.ps1 -BaseUrl http://127.0.0.1:5000 -Version 4
#
# If you see "model not found": restart Flask after editing config.py, run generate_insurance_model.py,
# and set MLFLOW_TRACKING_URI to match mlflow server (e.g. http://127.0.0.1:8080).

param(
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [string]$Version = "4"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

# Feature names must match training (get_dummies drop_first on sex, smoker, region).
$predictBody = @{
    features = @{
        age                = 46
        bmi                = 20.4
        children           = 2
        sex_male           = 0
        smoker_yes         = 0
        region_northwest   = 0
        region_southeast   = 0
        region_southwest   = 1
    }
    tags = @{ source = "final-demo" }
} | ConvertTo-Json -Depth 6

Write-Step "1) POST /insurance-charges/version/$Version/predict"
try {
    $pred = Invoke-RestMethod -Method POST `
        -Uri "$BaseUrl/insurance-charges/version/$Version/predict" `
        -ContentType "application/json; charset=utf-8" `
        -Body $predictBody
    $id = ([string]$pred.id).Trim()
    if (-not $id) {
        Write-Host "FAILED: predict response had no id." -ForegroundColor Red
        exit 1
    }
    Write-Host "prediction id: $id"
    Write-Host "label: $($pred.label)"
} catch {
    Write-Host "FAILED: $_" -ForegroundColor Red
    Write-Host "Ensure MLflow is running and config MODELS includes insurance-charges version $Version."
    exit 1
}

Write-Step "2) GET /prediction/$id"
$r2 = Invoke-RestMethod -Method GET -Uri "$BaseUrl/prediction/$id"
Write-Host "retrieved id: $($r2.id), label: $($r2.label)"

Write-Step "3) GET /prediction/$id/explainer"
# Avoid empty $id (merged URL becomes /prediction/explainer) and trailing-slash 308
# issues with Invoke-RestMethod on some PowerShell builds.
$explainerUrl = "$BaseUrl/prediction/$id/explainer".TrimEnd("/")
$r3 = Invoke-RestMethod -Method GET -Uri $explainerUrl
$sum = [string]$r3.summary
$len = [Math]::Min(200, $sum.Length)
if ($len -gt 0) {
    Write-Host "summary (first 200 chars): $($sum.Substring(0, $len))..."
} else {
    Write-Host "summary: (empty)"
}

Write-Step "4) Error demo - unknown model (expect 404)"
try {
    Invoke-RestMethod -Method POST `
        -Uri "$BaseUrl/does-not-exist-model/version/1/predict" `
        -ContentType "application/json" `
        -Body '{"features":{"x":1}}' `
        -ErrorAction Stop
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "HTTP $code (expected 404)"
}

Write-Step "Done"
Write-Host ('Use prediction id in slides or Arize UI: ' + $id)
