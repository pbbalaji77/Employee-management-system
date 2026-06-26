@echo off
title EMS Local Server Runner
cd /d "%~dp0"
echo ===================================================
echo   Enterprise EMS Local Server Auto-Restart Daemon
echo ===================================================
:loop
echo [%date% %time%] Starting Flask Server...
.\venv\Scripts\python app.py
echo [%date% %time%] Server stopped or crashed with exit code %errorlevel%.
echo Restarting server in 3 seconds...
timeout /t 3 >nul
goto loop
