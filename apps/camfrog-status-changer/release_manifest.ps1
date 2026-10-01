$ErrorActionPreference = "Stop"
$exe = Join-Path $PSScriptRoot "dist\CamfrogStatusChanger.exe"
if (!(Test-Path $exe)) { throw "EXE not found: $exe" }
$hash = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLower()
$manifest = [ordered]@{
  app = "Camfrog Status Changer"
  sha256 = $hash
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
}
$manifest | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot "dist\release-manifest.json")
Write-Host "SHA-256: $hash"
