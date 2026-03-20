$pol = Get-NetQosPolicy -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'PW_*' }
if ($pol) {
    $count = ($pol | Measure-Object).Count
    Write-Host "QoS: DIRTY - $count PW_* policies still present"
    $pol | Select-Object Name, ThrottleRateAction | Format-Table -AutoSize
} else {
    Write-Host "QoS: CLEAN - no PW_* policies"
}

$hosts = 'C:\Windows\System32\drivers\etc\hosts'
if (Test-Path $hosts) {
    $c = Get-Content $hosts -Raw -ErrorAction SilentlyContinue
    if ($c -match 'PathWise') {
        Write-Host "HOSTS: DIRTY - PathWise block present"
    } else {
        Write-Host "HOSTS: CLEAN - no PathWise block"
    }
}
