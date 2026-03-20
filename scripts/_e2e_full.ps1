param()

$ErrorActionPreference = 'Continue'
$results = [ordered]@{}

function Write-Section($t) { Write-Host ""; Write-Host "==== $t ====" -ForegroundColor Cyan }

function Invoke-Retry($name, $scriptblock, $attempts = 6, $delay = 2) {
    for ($i = 1; $i -le $attempts; $i++) {
        try { return & $scriptblock } catch {
            Write-Host ("  [{0}] attempt {1}/{2} failed: {3}" -f $name, $i, $attempts, $_.Exception.Message)
            Start-Sleep -Seconds $delay
        }
    }
    throw "$name failed after $attempts attempts"
}

Write-Section "0. Auth"
$token = Invoke-Retry -name "login" -scriptblock {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login/v2" `
        -Method Post -ContentType "application/json" `
        -Body '{"email":"marcus@riveralogistics.com","password":"Rivera@2026"}' -TimeoutSec 15
    if (-not $resp.access_token) { throw "no access_token in response" }
    return $resp.access_token
}
Write-Host "  Token acquired (len=$($token.Length))"
$authHdr = @{ Authorization = "Bearer $token" }

Invoke-Retry -name "reset" -scriptblock {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/apps/reset" -Method Post -Headers $authHdr -TimeoutSec 15 | Out-Null
} | Out-Null
Write-Host "  Reset OK."

Write-Section "1. Open YouTube video in Chrome"
Start-Process "chrome.exe" -ArgumentList "--new-window","https://www.youtube.com/watch?v=dQw4w9WgXcQ&autoplay=1"
Write-Host "  Waiting 20s for video to load + buffer..."
Start-Sleep -Seconds 20

Write-Section "2. Snapshot Chrome's Google CDN connections BEFORE apply"
$chromePids = (Get-Process chrome -ErrorAction SilentlyContinue).Id
$v4Prefixes = @("34.","35.","64.233.","66.102.","66.249.","72.14.","74.125.",
                "108.177.","142.250.","142.251.","172.217.","172.253.",
                "173.194.","192.178.","209.85.","216.58.","216.239.","18.97.")
$v6Prefixes = @("2607:f8b0","2a00:1450","2404:6800","2800:3f0","2c0f:fb50","2001:4860")

function Get-ChromeGoogleIPs {
    param($cpids)
    $tcp = Get-NetTCPConnection -OwningProcess $cpids -State Established -ErrorAction SilentlyContinue |
           Where-Object { $_.RemotePort -eq 443 } | Select-Object -ExpandProperty RemoteAddress
    @($tcp | Sort-Object -Unique) | Where-Object {
        $ip = $_
        if ($ip -like "*:*") { $v6Prefixes | Where-Object { $ip.ToLower().StartsWith($_) } }
        else { $v4Prefixes | Where-Object { $ip.StartsWith($_) } }
    }
}

$beforeGoog = @(Get-ChromeGoogleIPs -cpids $chromePids)
Write-Host "  Google-owned :443 IPs Chrome is using: $($beforeGoog.Count)"
$beforeGoog | ForEach-Object { Write-Host "    $_" }
$results["before_google_count"] = $beforeGoog.Count

Write-Section "3. Apply YouTube=LOW via API"
$body = '{"priorities":[{"app_id":"youtube","priority":"LOW"}]}'
$applyResp = Invoke-Retry -name "apply" -scriptblock {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/apps/priorities" `
        -Method Post -ContentType "application/json" -Headers $authHdr -Body $body -TimeoutSec 30
}
$ytRow = $applyResp.apps | Where-Object { $_.app_id -eq 'youtube' }
Write-Host "  Applied: $($applyResp.apps.Count) app(s). youtube quality=$($ytRow.estimated_quality), enforcement.active=$($applyResp.enforcement.active)"
Start-Sleep -Seconds 3  # firewall rules settle

Write-Section "4. Verify firewall rules CREATED"
$rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "PW_Disrupt*" }
Write-Host "  Disrupt rules: $($rules.Count)"
$allBlockedIps = @()
$rules | ForEach-Object {
    $addr = ($_ | Get-NetFirewallAddressFilter).RemoteAddress
    $flat = @($addr) -join ','
    Write-Host "    $($_.DisplayName): $flat"
    $allBlockedIps += @($addr)
}
$allBlockedIps = $allBlockedIps | Sort-Object -Unique
$results["disrupt_rules"] = $rules.Count
$results["blocked_ips"] = $allBlockedIps.Count

Write-Section "5a. Chrome connections +3s after apply"
$after3 = @(Get-ChromeGoogleIPs -cpids $chromePids)
Write-Host "  Google :443 IPs: $($after3.Count)"

Write-Section "5b. Chrome connections +15s after apply (TCP timeout window)"
Start-Sleep -Seconds 12
$afterGoog = @(Get-ChromeGoogleIPs -cpids $chromePids)
Write-Host "  Google :443 IPs: $($afterGoog.Count)"
$afterGoog | ForEach-Object { Write-Host "    $_" }
$results["after_google_count"] = $afterGoog.Count

# Did the rules actually target Chrome's IPs?
$ipOverlap = @($beforeGoog | Where-Object { $allBlockedIps -contains $_ })
Write-Host "  Overlap between Chrome's pre-apply IPs and blocked IPs: $($ipOverlap.Count)"
$ipOverlap | ForEach-Object { Write-Host "    match: $_" }
$results["ip_overlap"] = $ipOverlap.Count

Write-Section "6. Verify hosts block in effect"
$hostsFile = Get-Content 'C:\Windows\System32\drivers\etc\hosts' -Raw
if ($hostsFile -match "0\.0\.0\.0 .*youtube") { Write-Host "  Hosts: YES -- youtube blackholed" } else { Write-Host "  Hosts: NO block" }

Write-Section "6b. Verify NRPT wildcard DNS block"
$nrpt = Get-DnsClientNrptRule -ErrorAction SilentlyContinue | Where-Object { $_.Comment -eq 'PathWise-AppBlock' }
Write-Host "  NRPT rules: $($nrpt.Count)"
$nrpt | ForEach-Object { Write-Host "    namespaces: $($_.Namespace -join ', ') -> $($_.NameServers -join ', ')" }

Write-Section "6c. Test wildcard subdomain DNS"
$wild = try { (Resolve-DnsName -Name "r3---sn-xyz123.googlevideo.com" -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress) } catch { "FAILED" }
Write-Host "  r3---sn-xyz123.googlevideo.com -> $wild  (want 0.0.0.0)"
$results["wildcard_blocked"] = ($wild -eq "0.0.0.0")

Write-Section "7. Reachability test"
function Test-Url($u) {
    try { $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0; return $r.StatusCode }
    catch { if ($_.Exception.Message -match "redirect") { return 301 } else { return "BLOCKED" } }
}
$yt = Test-Url "https://www.youtube.com"
$gv = Test-Url "https://googlevideo.com"
$gh = Test-Url "https://github.com"
$gm = Test-Url "https://mail.google.com"
Write-Host "  youtube.com     : $yt  (want BLOCKED)"
Write-Host "  googlevideo.com : $gv  (want BLOCKED)"
Write-Host "  github.com      : $gh  (want 200/301)"
Write-Host "  mail.google.com : $gm  (want 200/301)"
$results["youtube_blocked"] = ($yt -eq "BLOCKED")
$results["github_works"]    = ($gh -in 200,301,302)

Write-Section "SUMMARY"
$dropped = $results["before_google_count"] - $results["after_google_count"]
Write-Host "  Chrome Google IPs dropped:   $($results['before_google_count']) -> $($results['after_google_count'])  (delta=$dropped)"
Write-Host "  Firewall rules installed:    $($results['disrupt_rules'])"
Write-Host "  IPs on Chrome matched by FW: $($results['ip_overlap']) / $($results['before_google_count'])"
Write-Host "  YouTube fetch blocked:       $($results['youtube_blocked'])"
Write-Host "  GitHub still works:          $($results['github_works'])"
Write-Host "  NRPT wildcard blocks dyn:    $($results['wildcard_blocked'])"
$pass = ($results["disrupt_rules"] -gt 0) -and `
        ($results["ip_overlap"] -gt 0 -or $results["before_google_count"] -eq 0) -and `
        $results["youtube_blocked"] -and $results["github_works"] -and `
        $results["wildcard_blocked"]
if ($pass) { Write-Host "  RESULT: PASS" -ForegroundColor Green; exit 0 }
else        { Write-Host "  RESULT: FAIL" -ForegroundColor Red; exit 1 }
