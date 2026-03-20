# Comprehensive YouTube-block sequence, standalone (no backend dependency).
# Must run elevated.

# 1) NRPT wildcard DNS redirect for every YouTube-ish host
Get-DnsClientNrptRule -ErrorAction SilentlyContinue |
  Where-Object { $_.Comment -eq 'PathWise-AppBlock' } |
  Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue
Add-DnsClientNrptRule -Namespace @('.youtube.com','.googlevideo.com','.ytimg.com',
    '.youtubei.googleapis.com','.youtu.be') -NameServers '0.0.0.0' `
    -Comment 'PathWise-AppBlock' -ErrorAction SilentlyContinue
Write-Host "[1/5] NRPT wildcard DNS rules installed."

# 2) Hosts-file block as a belt-and-suspenders for DNS
$hosts = 'C:\Windows\System32\drivers\etc\hosts'
$raw = Get-Content $hosts -Raw -ErrorAction SilentlyContinue
if ($raw -notmatch 'PathWise-Demo-YT') {
    $block = @"

# PathWise-Demo-YT BEGIN
0.0.0.0 www.youtube.com
0.0.0.0 m.youtube.com
0.0.0.0 youtube.com
0.0.0.0 youtu.be
0.0.0.0 www.googlevideo.com
0.0.0.0 googlevideo.com
0.0.0.0 i.ytimg.com
0.0.0.0 s.ytimg.com
0.0.0.0 youtubei.googleapis.com
# PathWise-Demo-YT END

"@
    Add-Content -Path $hosts -Value $block -Encoding ASCII
}
Write-Host "[2/5] Hosts-file block written."

# 3) Flush all DNS caches
Clear-DnsClientCache -ErrorAction SilentlyContinue
ipconfig /flushdns | Out-Null
Write-Host "[3/5] DNS cache flushed."

# 4) Kill Chrome's network service -- forces re-resolve of every host
$killed = 0
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like '*network.mojom.NetworkService*' } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    $killed++
  }
Write-Host "[4/5] Chrome network service killed ($killed processes) -- cached Alt-Svc entries gone."

# 5) Block outbound TCP+UDP :443 to Chrome's CURRENT Google IPs
$v4pref = @('34.','35.','74.125.','142.250.','142.251.','172.217.','172.253.','173.194.','18.97.','192.178.','209.85.','216.58.','216.239.')
$v6pref = @('2607:f8b0','2a00:1450','2404:6800','2800:3f0','2c0f:fb50','2001:4860')

Start-Sleep -Seconds 2  # let Chrome re-establish a few sockets after the kill

$cpids = (Get-Process chrome -ErrorAction SilentlyContinue).Id
$ips = @()
if ($cpids) {
    $all = Get-NetTCPConnection -OwningProcess $cpids -State Established -ErrorAction SilentlyContinue |
           Where-Object { $_.RemotePort -eq 443 } | Select-Object -ExpandProperty RemoteAddress -Unique
    foreach ($ip in $all) {
        if ($ip -like '*:*') {
            foreach ($p in $v6pref) { if ($ip.ToLower().StartsWith($p)) { $ips += $ip; break } }
        } else {
            foreach ($p in $v4pref) { if ($ip.StartsWith($p)) { $ips += $ip; break } }
        }
    }
}

Get-NetFirewallRule -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -like 'PW_DemoYT*' } |
  Remove-NetFirewallRule -ErrorAction SilentlyContinue

if ($ips.Count -gt 0) {
    $v4 = $ips | Where-Object { $_ -notlike '*:*' }
    $v6 = $ips | Where-Object { $_ -like '*:*' }
    if ($v4) {
        New-NetFirewallRule -DisplayName 'PW_DemoYT_TCP_v4' -Direction Outbound -Action Block `
            -Protocol TCP -RemoteAddress ($v4 -join ',') -RemotePort 443 -Enabled True `
            -ErrorAction SilentlyContinue | Out-Null
        New-NetFirewallRule -DisplayName 'PW_DemoYT_UDP_v4' -Direction Outbound -Action Block `
            -Protocol UDP -RemoteAddress ($v4 -join ',') -RemotePort 443 -Enabled True `
            -ErrorAction SilentlyContinue | Out-Null
    }
    if ($v6) {
        New-NetFirewallRule -DisplayName 'PW_DemoYT_TCP_v6' -Direction Outbound -Action Block `
            -Protocol TCP -RemoteAddress ($v6 -join ',') -RemotePort 443 -Enabled True `
            -ErrorAction SilentlyContinue | Out-Null
        New-NetFirewallRule -DisplayName 'PW_DemoYT_UDP_v6' -Direction Outbound -Action Block `
            -Protocol UDP -RemoteAddress ($v6 -join ',') -RemotePort 443 -Enabled True `
            -ErrorAction SilentlyContinue | Out-Null
    }
}
# Block QUIC globally
New-NetFirewallRule -DisplayName 'PW_DemoYT_QUIC_all' -Direction Outbound -Action Block `
    -Protocol UDP -RemotePort 443 -Enabled True -ErrorAction SilentlyContinue | Out-Null

Write-Host "[5/5] Firewall: blocked $($ips.Count) live IPs + global QUIC."
Write-Host ""
Write-Host "======================================"
Write-Host "DONE. YouTube should stall within 5s."
Write-Host "Run _unblock_youtube.ps1 to restore."
Write-Host "======================================"
