$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$exe = Join-Path $PSScriptRoot 'dist\CamfrogStatusChanger.exe'
if (-not (Test-Path $exe)) { throw "Missing $exe" }
$hash = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLowerInvariant()
$size = (Get-Item $exe).Length
$versionLine = Select-String -Path (Join-Path $PSScriptRoot 'version.py') -Pattern '^VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
$version = if ($versionLine -and $versionLine.Matches.Count -gt 0) { $versionLine.Matches[0].Groups[1].Value } else { 'unknown' }
$manifest = [ordered]@{
  artifact = 'CamfrogStatusChanger.exe'
  version = $version
  sha256 = $hash
  size_bytes = $size
  built_utc = (Get-Date).ToUniversalTime().ToString('o')
  platform = 'windows-x64'
  native_profile_mode = 'version-gated-static-profile; internal-RVA-invocation-disabled'
}
$manifest | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'dist\release-manifest.json')
Write-Host "Version: $version"
Write-Host "SHA256: $hash"
