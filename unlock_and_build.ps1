$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$app = 'CamfrogStatusChanger'
$exe = Join-Path $PSScriptRoot "dist\$app.exe"

Write-Host "Stopping running $app instances..."
Get-Process -Name $app -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 800

if (Test-Path $exe) {
    try {
        Remove-Item -LiteralPath $exe -Force
    } catch {
        Write-Error "The old EXE is still locked: $exe`nClose Explorer Preview Pane, debugger, antivirus scan, or running copies and retry."
    }
}

& cmd.exe /c "`"$PSScriptRoot\build_exe_fixed.bat`""
exit $LASTEXITCODE
