# PSA SAP — início rápido (sem reinstalar nada).
# Use este no dia a dia; o run.ps1 é só para a primeira vez ou após mudar o código.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

Write-Host ""
Write-Host "  PSA SAP subindo em  http://localhost:8000" -ForegroundColor Green
Write-Host "  (deixe esta janela aberta; Ctrl+C encerra)" -ForegroundColor DarkGray
Write-Host ""

Start-Process "http://localhost:8000"   # abre no navegador padrão (Chrome)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
