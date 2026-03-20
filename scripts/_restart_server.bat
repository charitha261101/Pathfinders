@echo off
:: Internal helper -- kills any uvicorn on :8000 then relaunches the enforcer
net session >nul 2>&1 || ( echo Must run elevated & pause & exit /b 1 )

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo Killing PID %%a ...
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 2 >nul

set ENFORCER_MODE=powershell
set WAN_INTERFACE=eth0
set TOTAL_LINK_MBPS=100
set DATA_SOURCE=sim

cd /d "C:\Users\vinee\Desktop\PATHWISEAI"
start "PathWise AI" cmd /k python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
exit /b 0
