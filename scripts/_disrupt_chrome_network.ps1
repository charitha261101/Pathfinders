# Kill Chrome's network service (utility) process -- this forces Chrome to
# drop all its cached Alt-Svc entries, TCP connections, and QUIC sessions.
# Chrome auto-respawns the network service but must re-resolve every host,
# so our hosts+NRPT blocks take effect immediately.

$net = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like '*--utility-sub-type=network.mojom.NetworkService*'
}

if (-not $net) {
    # Fallback: use WMI to match command line (Get-Process doesn't always expose CommandLine)
    $net = Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like '*network.mojom.NetworkService*' } |
           ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
}

if ($net) {
    foreach ($p in $net) {
        Write-Host "Killing Chrome network service PID $($p.Id) ..."
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done -- Chrome will auto-respawn network service with clean cache."
} else {
    Write-Host "No Chrome network service process found."
}
