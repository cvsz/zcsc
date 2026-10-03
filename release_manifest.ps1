param(
  [string]$ArtifactPath = (Join-Path $PSScriptRoot 'dist\CamfrogStatusChanger.exe'),
  [string]$OutputPath = (Join-Path $PSScriptRoot 'dist\release-manifest.json')
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'scripts\write_release_manifest.py'
& python $scriptPath --artifact $ArtifactPath --output $OutputPath
if ($LASTEXITCODE -ne 0) {
  throw "Manifest generation failed with exit code $LASTEXITCODE"
}
