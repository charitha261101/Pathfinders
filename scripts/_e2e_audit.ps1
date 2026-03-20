param()

Write-Host "=== STEP 1: Chrome live connections BEFORE apply ==="
$pids = (Get-Process chrome -ErrorAction SilentlyContinue).Id
if (-not $pids) {
    Write-Host "NO CHROME RUNNING -- cannot test. Please open YouTube first."
    exit 1
}
Write-Host "Chrome PIDs: $($pids.Count) processes"
$tcpBefore = Get-NetTCPConnection -OwningProcess $pids -State Established -ErrorAction SilentlyContinue |
             Where-Object { $_.RemotePort -eq 443 }
$beforeIps = $tcpBefore | Select-Object -ExpandProperty RemoteAddress -Unique
Write-Host "TCP :443 connections: $($tcpBefore.Count), unique IPs: $($beforeIps.Count)"
$beforeIps | Select-Object -First 15 | ForEach-Object { Write-Host "  $_" }

Write-Host ""
Write-Host "=== STEP 2: Test reachability BEFORE ==="
$yt = try { (Invoke-WebRequest -Uri "https://www.youtube.com" -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0).StatusCode } catch { "ERR:$($_.Exception.Message.Substring(0, [Math]::Min(50, $_.Exception.Message.Length)))" }
$gv = try { (Invoke-WebRequest -Uri "https://googlevideo.com" -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0).StatusCode } catch { "ERR" }
$gh = try { (Invoke-WebRequest -Uri "https://github.com" -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0).StatusCode } catch { "ERR" }
Write-Host "  youtube.com     : $yt"
Write-Host "  googlevideo.com : $gv"
Write-Host "  github.com      : $gh"
