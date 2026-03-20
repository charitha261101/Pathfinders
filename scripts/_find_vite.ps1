Write-Host "--- non-Adobe node processes ---"
Get-Process node -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -notmatch 'Adobe'
} | Select-Object Id, StartTime, Path | Format-List

Write-Host "--- cmd windows with Vite/PathWise in title ---"
Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match 'PathWise|Vite|Frontend|npm'
} | Select-Object Id, MainWindowTitle | Format-List

Write-Host "--- listeners 3000-5175 ---"
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -ge 3000 -and $_.LocalPort -le 5175 } |
    Select-Object LocalPort, OwningProcess |
    Format-Table -AutoSize

Write-Host "--- node_modules exists? ---"
if (Test-Path 'C:\Users\vinee\Desktop\PATHWISEAI\frontend\node_modules\vite') {
    Write-Host "  vite installed: YES"
} else {
    Write-Host "  vite installed: NO -- run 'npm install' in frontend/"
}

Write-Host "--- try vite --version ---"
Push-Location 'C:\Users\vinee\Desktop\PATHWISEAI\frontend'
& npx vite --version 2>&1
Pop-Location
