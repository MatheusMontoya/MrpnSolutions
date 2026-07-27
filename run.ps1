# PSA SAP — instala, builda o frontend e sobe o app em http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/3] Dependencias do backend..." -ForegroundColor Cyan
python -m pip install -q -r backend\requirements.txt

Write-Host "[2/3] Build do frontend..." -ForegroundColor Cyan
npm --prefix frontend install --no-fund --no-audit
npm --prefix frontend run build

Write-Host "[3/3] Subindo PSA SAP em http://127.0.0.1:8000 (docs em /docs)" -ForegroundColor Green
Set-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
