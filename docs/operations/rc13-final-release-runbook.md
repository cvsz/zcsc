# RC13 Final Release Runbook

This runbook covers the remaining operator-only gates after GitHub CI, CodeQL, Dependency Review, Windows packaging, PE/x64 verification, and Microsoft Defender scanning have passed.

## Boundary

A green CI build is not proof of live Camfrog publication. Do not call RC13 production-ready until `scripts/validate_live_evidence.py` accepts an evidence file produced from the exact source commit and the exact Camfrog executable tested.

Do not record passwords, session tokens, cookies, private chat text, phone numbers, email addresses, or account identifiers in evidence notes.

## 1. Prepare the exact checkout

On the Windows machine used for interactive testing:

```powershell
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD
py -3 -c "import version; print(version.VERSION)"
```

Expected source version: `2.2.5-rc13`.

Use the exact built candidate corresponding to that source revision. Do not substitute an older RC binary. The checkout must be clean; the collector refuses evidence collection if tracked or untracked worktree changes are present.

## 2. Run live validation collector

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_live_evidence.ps1 `
  -ApplicationPath .\dist\CamfrogStatusChanger.exe `
  -ManifestPath .\dist\release-manifest.json
```

If Camfrog is installed elsewhere:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_live_evidence.ps1 -CamfrogPath "C:\path\to\Camfrog Video Chat.exe"
```

The collector verifies the application candidate against its release manifest first, then records the exact application SHA-256/size/manifest identity, project version and Git SHA, Windows build information, Camfrog executable hash/version, Defender status, and all ten P0 gate outcomes. It does not sign in, read credentials, or automatically send room actions.

## 3. Required live gates

Every gate must be `pass`:

1. server-visible status from an independent session/account
2. minimized/not-focused status apply
3. reconnect/login persistence or correct reconciliation
4. sequential and random rotation for at least ten controlled cycles
5. focus/Enter behavior without physical mouse movement or cross-app typing
6. selector stability after restart/update, including fail-closed ambiguity
7. startup/tray/single-instance/log rotation/clean exit
8. final exact EXE Defender/organizational malware scan without exclusions
9. current Camfrog policy/terms review for intended distribution/use
10. controlled-room E2E for confirmation, Auto kick, cooldown, exact-room targeting, and false-positive behavior

Use test accounts and a controlled room.

## 4. Validate evidence

```powershell
py -3 .\scripts\validate_live_evidence.py .\evidence\YYYYMMDD-HHMMSS\live-validation.json
```

Pin the evidence to the exact release commit:

```powershell
$sha = git rev-parse HEAD
py -3 .\scripts\validate_live_evidence.py .\evidence\YYYYMMDD-HHMMSS\live-validation.json --expected-git-sha $sha
```

Only a zero exit code is a production evidence pass.

## 5. Signing and SmartScreen

RC13 is not code-signed by repository CI. Before broad distribution:

- sign the final EXE with an appropriate Windows code-signing certificate
- verify Authenticode on the exact distributed binary
- retain the signed binary SHA-256
- test SmartScreen/reputation behavior without adding exclusions or bypass instructions
- re-run Defender/organizational scanning on the signed binary

Signing changes the binary, so its SHA-256 becomes a new distribution artifact identity.

## 6. Release decision

Promote to final only when required GitHub checks are green, packaging/manifest/PE/Defender gates are green, live validation JSON passes, signing/SmartScreen checks are complete for the distributed binary, and the policy review is passed. Otherwise keep the build labeled release candidate.
