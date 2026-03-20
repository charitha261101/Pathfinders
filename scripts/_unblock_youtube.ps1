# Reverse everything _apply_youtube_block_full.ps1 did.
Get-NetFirewallRule -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -like 'PW_DemoYT*' -or $_.DisplayName -like 'PW_Disrupt*' } |
  Remove-NetFirewallRule -ErrorAction SilentlyContinue
Write-Host "[1/3] Firewall rules removed."

Get-DnsClientNrptRule -ErrorAction SilentlyContinue |
  Where-Object { $_.Comment -eq 'PathWise-AppBlock' } |
  Remove-DnsClientNrptRule -Force -ErrorAction SilentlyContinue
Write-Host "[2/3] NRPT rules removed."

$hosts = 'C:\Windows\System32\drivers\etc\hosts'
$raw = Get-Content $hosts -Raw -ErrorAction SilentlyContinue
$changed = $false
if ($raw -match 'PathWise-Demo-YT') {
    $raw = [regex]::Replace($raw, '(?s)\s*# PathWise-Demo-YT BEGIN.*?# PathWise-Demo-YT END\s*', "`r`n")
    $changed = $true
}
if ($raw -match '=== PathWise AI BEGIN ===') {
    $raw = [regex]::Replace($raw, '(?s)\s*# === PathWise AI BEGIN ===.*?# === PathWise AI END ===\s*', "`r`n")
    $changed = $true
}
if ($changed) {
    Set-Content -Path $hosts -Value $raw.TrimEnd() -Encoding ASCII -Force
    Write-Host "[3/3] Hosts-file block removed."
} else {
    Write-Host "[3/3] No PathWise hosts block found."
}

Clear-DnsClientCache -ErrorAction SilentlyContinue
ipconfig /flushdns | Out-Null
Write-Host ""
Write-Host "RESTORED. YouTube should work again (refresh the tab)."
