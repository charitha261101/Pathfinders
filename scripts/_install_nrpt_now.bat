@echo off
:: Install Windows NRPT wildcard DNS blocks for YouTube right now.
:: No server restart needed -- this directly installs at OS level.
title PathWise AI -- NRPT wildcard DNS block
net session >nul 2>&1 || ( echo Must run as admin & pause & exit /b 1 )

echo Removing any stale PathWise NRPT rules...
powershell -NoProfile -Command ^
    "Get-DnsClientNrptRule -ErrorAction SilentlyContinue | Where-Object { $_.Comment -eq 'PathWise-AppBlock' } | Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue"

echo Installing wildcard DNS block for YouTube subdomains...
powershell -NoProfile -Command ^
    "Add-DnsClientNrptRule -Namespace @('.youtube.com','.googlevideo.com','.ytimg.com','.youtubei.googleapis.com','.youtu.be') -NameServers '0.0.0.0' -Comment 'PathWise-AppBlock'"

echo Flushing DNS cache...
ipconfig /flushdns >nul
powershell -NoProfile -Command "Clear-DnsClientCache -ErrorAction SilentlyContinue"

echo Verifying...
powershell -NoProfile -Command ^
    "$r = Resolve-DnsName -Name 'r1---sn-fake.googlevideo.com' -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress; Write-Host ('  r1---sn-fake.googlevideo.com -> ' + $r)"
powershell -NoProfile -Command ^
    "$r = Resolve-DnsName -Name 'www.youtube.com' -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress; Write-Host ('  www.youtube.com -> ' + $r)"
powershell -NoProfile -Command ^
    "$r = Resolve-DnsName -Name 'mail.google.com' -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress; Write-Host ('  mail.google.com -> ' + $r + ' (should be REAL IP, not 0.0.0.0)')"

echo.
echo Done. Refresh YouTube tab in Chrome to see the block.
timeout /t 5 >nul
