param()

Write-Host "=== Chrome's Google-CDN :443 connections state ==="
$pids = (Get-Process chrome -ErrorAction SilentlyContinue).Id
if (-not $pids) { Write-Host "No Chrome running"; exit }

$conns = Get-NetTCPConnection -OwningProcess $pids -State Established -ErrorAction SilentlyContinue |
         Where-Object { $_.RemotePort -eq 443 }
$v4 = @("34.","35.","74.125.","142.250.","142.251.","172.217.","172.253.","173.194.","18.97.","192.178.","209.85.","216.58.","216.239.")
$v6 = @("2607:f8b0","2a00:1450","2404:6800","2800:3f0","2c0f:fb50","2001:4860")

$googCnt = 0
foreach ($c in $conns) {
    $ip = $c.RemoteAddress
    $match = $false
    if ($ip -like "*:*") {
        foreach ($p in $v6) { if ($ip.ToLower().StartsWith($p)) { $match = $true; break } }
    } else {
        foreach ($p in $v4) { if ($ip.StartsWith($p)) { $match = $true; break } }
    }
    if ($match) { $googCnt++ }
}
Write-Host "Total :443: $($conns.Count)  Google-owned: $googCnt"

Write-Host ""
Write-Host "=== Direct TCP connect test to known IPs (NetTest) ==="
# Test-NetConnection on a YouTube IP that SHOULD be blocked by our firewall
$test1 = Test-NetConnection -ComputerName "142.251.116.106" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
Write-Host "  142.251.116.106:443 (in PW_Disrupt list): $(if ($test1) {'REACHABLE (FW failed)'} else {'BLOCKED (ok)'})"

$test2 = Test-NetConnection -ComputerName "142.250.113.18" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
Write-Host "  142.250.113.18:443 (NOT in PW list): $(if ($test2) {'REACHABLE (expected)'} else {'BLOCKED'})"

$test3 = Test-NetConnection -ComputerName "140.82.112.25" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
Write-Host "  140.82.112.25:443 (GitHub): $(if ($test3) {'REACHABLE (ok)'} else {'BLOCKED (bad)'})"

Write-Host ""
Write-Host "=== Active firewall block rules ==="
Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like 'PW_Disrupt*' } |
    ForEach-Object {
        $addr = ($_ | Get-NetFirewallAddressFilter).RemoteAddress
        $proto = ($_ | Get-NetFirewallPortFilter).Protocol
        Write-Host ("  {0}  proto={1}  addrs={2}" -f $_.DisplayName, $proto, (@($addr) -join ','))
    }

Write-Host ""
Write-Host "=== NRPT rules ==="
Get-DnsClientNrptRule -ErrorAction SilentlyContinue | Where-Object { $_.Comment -eq 'PathWise-AppBlock' } |
    ForEach-Object { Write-Host ("  {0} -> {1}" -f ($_.Namespace -join ','), ($_.NameServers -join ',')) }

Write-Host ""
Write-Host "=== DNS resolution via Windows resolver ==="
$dyn = Resolve-DnsName -Name "r3---sn-a5mekne7.googlevideo.com" -Type A -QuickTimeout -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress
Write-Host "  r3---sn-a5mekne7.googlevideo.com -> '$dyn'  (want 0.0.0.0 or empty)"
$yt = Resolve-DnsName -Name "www.youtube.com" -Type A -QuickTimeout -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress
Write-Host "  www.youtube.com -> '$yt'  (want 0.0.0.0)"
$gm = Resolve-DnsName -Name "mail.google.com" -Type A -QuickTimeout -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress
Write-Host "  mail.google.com -> '$gm'  (want a real IP)"
