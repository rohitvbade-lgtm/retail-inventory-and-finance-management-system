@echo off
echo ========================================================
echo Launching Full Stack POS & AI Discount Machine System
echo ========================================================
start "POS Backend Server (FastAPI)" cmd /k "%~dp0run_backend.bat"
timeout /t 3 /nobreak >nul
start "POS Frontend Application (Angular)" cmd /k "%~dp0run_frontend.bat"
echo Servers launched! Backend on http://localhost:8000 | Frontend on http://localhost:4200

