@echo off
:: PathWise AI -- PANIC / ROLLBACK script
:: Removes every trace of PathWise enforcement and restores internet.
:: Run as Administrator (right-click -> Run as administrator).

echo ============================================
echo  PathWise AI -- PANIC CLEANUP
echo ============================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Must run as Administrator.
    echo Right-click clear_qos_panic.bat -^> Run as administrator.
    pause
    exit /b 1
)

echo [1/4] Removing all PathWise NetQoS policies, firewall rules, NRPT rules...
powershell.exe -NoProfile -NonInteractive -Command ^
    "Get-NetQosPolicy -ErrorAction SilentlyContinue | Where-Object {$_.Name -like 'PW_*'} | Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue; Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -like 'PW_Disrupt*'} | Remove-NetFirewallRule -ErrorAction SilentlyContinue; Get-DnsClientNrptRule -ErrorAction SilentlyContinue | Where-Object { $_.Comment -eq 'PathWise-AppBlock' } | Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue; Write-Host 'QoS + firewall + NRPT rules cleared.'"

echo [2/4] Stripping PathWise block from hosts file...
powershell.exe -NoProfile -NonInteractive -Command ^
    "$hosts='C:\Windows\System32\drivers\etc\hosts'; $c=Get-Content $hosts -Raw -ErrorAction SilentlyContinue; if ($c -match '# === PathWise AI BEGIN ===') { $pattern='(?s)# === PathWise AI BEGIN ===.*?# === PathWise AI END ===\s*'; $new=[regex]::Replace($c, $pattern, ''); Set-Content -Path $hosts -Value $new.TrimEnd() -Encoding ASCII -Force; Write-Host 'Hosts file restored.' } else { Write-Host 'No PathWise block in hosts file.' }"

echo [3/4] Flushing DNS cache...
ipconfig /flushdns >nul 2>&1
echo DNS cache flushed.

echo [4/4] Resetting Winsock and releasing DHCP (optional)...
:: Uncomment if networking is still broken after steps 1-3:
:: netsh winsock reset
:: ipconfig /release
:: ipconfig /renew

echo.
echo ============================================
echo  Cleanup complete. Internet should work now.
echo ============================================
echo.
pause
