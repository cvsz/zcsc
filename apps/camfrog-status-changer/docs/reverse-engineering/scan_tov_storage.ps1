# Read-only Camfrog Text Over Video settings discovery.
# Does NOT write registry values or files.
$ErrorActionPreference = 'SilentlyContinue'

$names = @(
  'TOV_MigratedFromCF6','TOV_Enable','TOV_Text','TOV_FontName','TOV_Italic',
  'TOV_Bold','TOV_FontSize','TOV_BackgroundColor','TOV_TextColor',
  'TOV_HorizontalAlignment','TOV_VerticalAlignment','TOV_Transparent'
)

$results = @()
$roots = @(
  'HKCU:\Software\Camfrog',
  'HKCU:\Software\WOW6432Node\Camfrog'
)

foreach ($root in $roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem -Path $root -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $key = $_
    $props = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue
    foreach ($name in $names) {
      if ($null -ne $props -and $props.PSObject.Properties.Name -contains $name) {
        $value = $props.$name
        $results += [pscustomobject]@{
          Path = $key.Name
          Name = $name
          Type = if ($null -eq $value) { 'null' } else { $value.GetType().FullName }
          Value = $value
        }
      }
    }
  }
}

# Also inspect likely Camfrog local configuration files for literal TOV_ keys.
$fileHits = @()
$dirs = @($env:APPDATA, $env:LOCALAPPDATA) | Where-Object { $_ }
foreach ($base in $dirs) {
  Get-ChildItem -Path $base -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match 'Camfrog' -and $_.Length -lt 20MB } |
    ForEach-Object {
      $f = $_
      try {
        $raw = [System.IO.File]::ReadAllBytes($f.FullName)
        $ascii = [System.Text.Encoding]::UTF8.GetString($raw)
        $utf16 = [System.Text.Encoding]::Unicode.GetString($raw)
        $matched = $false
        foreach ($name in $names) {
          if ($ascii.Contains($name) -or $utf16.Contains($name)) { $matched = $true; break }
        }
        if ($matched) {
          $fileHits += [pscustomobject]@{
            Path = $f.FullName
            Size = $f.Length
            LastWriteTime = $f.LastWriteTime
          }
        }
      } catch {}
    }
}

$out = [pscustomobject]@{
  GeneratedAt = (Get-Date).ToString('o')
  RegistryValues = $results
  CandidateFiles = $fileHits
}

$dest = Join-Path $env:USERPROFILE 'Desktop\camfrog-tov-storage.json'
$out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $dest -Encoding UTF8
Write-Host "Saved: $dest"
Write-Host "Registry TOV values found: $($results.Count)"
Write-Host "Candidate config files found: $($fileHits.Count)"
