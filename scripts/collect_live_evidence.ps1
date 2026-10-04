param(
    [string]$OutputDirectory = "",
    [string]$CamfrogPath = "",
    [string]$ApplicationPath = "",
    [string]$ManifestPath = "",
    [string]$ExpectedVersion = "2.2.5-rc12"
)

$ErrorActionPreference = "Stop"

function Read-GateResult {
    param([string]$Id, [string]$Prompt)

    while ($true) {
        $answer = Read-Host "$Prompt [pass/fail/skip]"
        switch ($answer.Trim().ToLowerInvariant()) {
            "pass" { $status = "pass"; break }
            "fail" { $status = "fail"; break }
            "skip" { $status = "skip"; break }
            default {
                Write-Host "Enter pass, fail, or skip."
                continue
            }
        }
        break
    }

    $notes = Read-Host "Notes/evidence reference for $Id (optional)"
    return [ordered]@{ id = $Id; status = $status; notes = $notes }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $repoRoot "version.py"
if (-not (Test-Path $versionFile)) { throw "version.py not found at $versionFile" }

$versionText = Get-Content -Raw -Encoding UTF8 $versionFile
$match = [regex]::Match($versionText, 'VERSION\s*=\s*"([^"]+)"')
if (-not $match.Success) { throw "Unable to read VERSION from version.py" }
$sourceVersion = $match.Groups[1].Value
if ($sourceVersion -ne $ExpectedVersion) {
    throw "Source version $sourceVersion does not match expected $ExpectedVersion"
}

$gitSha = (& git -C $repoRoot rev-parse HEAD 2>$null).Trim()
if (-not $gitSha) { throw "Unable to resolve exact Git commit. Run this from a Git checkout." }

$dirty = & git -C $repoRoot status --porcelain 2>$null
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git worktree state." }
if ($dirty) {
    throw "Refusing live evidence collection from a dirty checkout. Commit/stash/revert local changes first."
}

if (-not $ApplicationPath) {
    $ApplicationPath = Join-Path $repoRoot "dist\CamfrogStatusChanger.exe"
}
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $repoRoot "dist\release-manifest.json"
}
if (-not (Test-Path $ApplicationPath)) {
    throw "Application candidate not found: $ApplicationPath"
}
if (-not (Test-Path $ManifestPath)) {
    throw "Release manifest not found: $ManifestPath"
}

$appHash = (Get-FileHash -Algorithm SHA256 -Path $ApplicationPath).Hash.ToLowerInvariant()
$appSize = (Get-Item $ApplicationPath).Length
$manifest = Get-Content -Raw -Encoding UTF8 $ManifestPath | ConvertFrom-Json
if ($manifest.artifact -ne (Split-Path -Leaf $ApplicationPath)) {
    throw "Manifest artifact name does not match the application candidate."
}
if ($manifest.version -ne $sourceVersion) {
    throw "Manifest version $($manifest.version) does not match source version $sourceVersion."
}
if ($manifest.sha256 -ne $appHash) {
    throw "Manifest SHA-256 does not match the application candidate."
}
if ([int64]$manifest.size_bytes -ne [int64]$appSize) {
    throw "Manifest size does not match the application candidate."
}

if (-not $CamfrogPath) {
    $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Camfrog Video Chat\Camfrog Video Chat.exe"),
        (Join-Path $env:ProgramFiles "Camfrog\Camfrog Video Chat\Camfrog Video Chat.exe"),
        $(if ($programFilesX86) { Join-Path $programFilesX86 "Camfrog\Camfrog Video Chat\Camfrog Video Chat.exe" })
    )
    $CamfrogPath = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $CamfrogPath -or -not (Test-Path $CamfrogPath)) {
    throw "Camfrog executable not found. Pass -CamfrogPath explicitly."
}

if (-not $OutputDirectory) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDirectory = Join-Path $repoRoot "evidence\$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$camfrogHash = (Get-FileHash -Algorithm SHA256 -Path $CamfrogPath).Hash.ToLowerInvariant()
$camfrogInfo = (Get-Item $CamfrogPath).VersionInfo

try {
    $defender = Get-MpComputerStatus |
        Select-Object AMServiceEnabled, AntivirusEnabled, AntispywareEnabled, RealTimeProtectionEnabled, AntivirusSignatureVersion, AntivirusSignatureLastUpdated
} catch {
    $defender = [ordered]@{ error = $_.Exception.Message }
}

Write-Host ""
Write-Host "RC12 live validation collector"
Write-Host "Source version: $sourceVersion"
Write-Host "Git SHA: $gitSha"
Write-Host "Application: $ApplicationPath"
Write-Host "Application SHA256: $appHash"
Write-Host "Camfrog: $CamfrogPath"
Write-Host "Camfrog SHA256: $camfrogHash"
Write-Host ""
Write-Host "Run each validation manually in a controlled test account/room."
Write-Host "Do not paste passwords, tokens, private chat text, or personal identifiers into notes."
Write-Host ""

$gates = @()
$gates += Read-GateResult "server_visible_status" "From an independent Camfrog account/session, is the applied custom status visible exactly?"
$gates += Read-GateResult "minimized_status" "While Camfrog is minimized/not focused, does Apply change the server-visible status without typing into another app?"
$gates += Read-GateResult "reconnect_persistence" "After reconnect/login refresh, does the expected status survive or reconcile correctly?"
$gates += Read-GateResult "rotation_10_cycles" "Did sequential and random rotation each complete at least 10 controlled cycles with one status per tick?"
$gates += Read-GateResult "focus_and_mouse_safety" "During verified foreground Enter commit, was Camfrog focused only as needed and was the physical mouse not moved?"
$gates += Read-GateResult "selector_stability" "After Camfrog restart/update, did exact status control targeting remain unique and fail closed on ambiguity?"
$gates += Read-GateResult "startup_tray_single_instance" "Did startup, tray close/reopen, single-instance, log rotation, and clean exit behave correctly?"
$gates += Read-GateResult "defender_scan" "Did the final exact EXE pass Microsoft Defender/organizational malware scan without exclusions?"
$gates += Read-GateResult "policy_review" "Has the intended automation use been reviewed against current Camfrog terms/policies for this distribution?"
$gates += Read-GateResult "controlled_room_e2e" "In a controlled room with test accounts, did manual confirmation/Auto kick/cooldown/exact-room targeting behave as expected with no false-positive action?"

$allPass = ($gates | Where-Object { $_.status -ne "pass" }).Count -eq 0

$os = Get-CimInstance Win32_OperatingSystem
$evidence = [ordered]@{
    schema_version = 1
    generated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source = [ordered]@{ version = $sourceVersion; git_sha = $gitSha }
    application = [ordered]@{
        executable_path = $ApplicationPath
        sha256 = $appHash
        size_bytes = $appSize
        manifest_path = $ManifestPath
        manifest_sha256 = (Get-FileHash -Algorithm SHA256 -Path $ManifestPath).Hash.ToLowerInvariant()
    }
    windows = [ordered]@{ edition = $os.Caption; version = $os.Version; build = $os.BuildNumber }
    camfrog = [ordered]@{
        executable_path = $CamfrogPath
        sha256 = $camfrogHash
        file_version = $camfrogInfo.FileVersion
        product_version = $camfrogInfo.ProductVersion
    }
    defender = $defender
    gates = $gates
    production_gate_passed = $allPass
    privacy_notice = "Evidence notes must not contain passwords, tokens, private chats, or personal identifiers."
}

$outputPath = Join-Path $OutputDirectory "live-validation.json"
$evidence | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $outputPath
Write-Host ""
Write-Host "Evidence written to: $outputPath"
if ($allPass) {
    Write-Host "All required live gates are PASS."
    exit 0
}
Write-Warning "One or more live gates are fail/skip. Production-ready must not be claimed."
exit 2
