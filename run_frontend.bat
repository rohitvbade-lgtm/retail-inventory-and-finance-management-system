@echo off
echo ========================================================
echo Starting Angular POS & Finance Frontend
echo ========================================================
cd /d "%~dp0\frontend"
npm start -- --port 4200 --open

