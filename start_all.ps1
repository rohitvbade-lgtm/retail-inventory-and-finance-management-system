# Launch both Backend and Frontend
$root = $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Launching Full Stack POS & AI Discount Machine System" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$root\run_backend.ps1"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$root\run_frontend.ps1"

Write-Host "Servers launched! Backend: http://127.0.0.1:8000 | Frontend: http://localhost:4200" -ForegroundColor Green
