@echo off
title PathWise AI -- Hard Restart
net session >nul 2>&1 || ( echo Must be admin & pause & exit /b 1 )

echo Killing ALL Python processes listening on :8000 ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /PID %%p /F /T
)
echo Waiting 3s for port to free...
timeout /t 3 /nobreak >nul

echo Starting fresh uvicorn in new window...
set ENFORCER_MODE=powershell
set WAN_INTERFACE=eth0
set TOTAL_LINK_MBPS=100
set DATA_SOURCE=sim
cd /d C:\Users\vinee\Desktop\PATHWISEAI
start "PathWise AI Backend" cmd /k "python -m uvicorn server.main:app --host 0.0.0.0 --port 8000"
echo Done.
