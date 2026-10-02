# Camfrog Status Changer

This folder is an optional Windows application/profile inside the reusable `ztemplate` repository.

Current candidate: **2.3.2-rc5 hybrid pywinauto**

## Features

- four independent status messages
- one tick = one message = one apply attempt
- seconds/minutes/hours intervals
- sequential/random rotation
- background-first native automation
- explicit foreground fallback
- TH/EN UI
- read-only Camfrog status-history discovery
- Unicode color markers and text-frame marquee
- known Camfrog binary fingerprint profile
- rotating logs, config recovery and single-instance guard
- Windows startup and system tray
- safe diagnostics and release SHA-256 manifest
- PyInstaller hidden-console build with `app.ico`

## Development

```cmd
run_dev.bat
```

## Self-test

```cmd
py self_test.py
```

Writes:

```text
%APPDATA%\CamfrogStatusChanger\self-test.json
```

## Camfrog diagnostics

```cmd
py diagnose_camfrog.py
py registry_history_dump.py
```

Outputs are sanitized and do not intentionally collect passwords, tokens, cookies or session material.

## Build

```cmd
build_exe_fixed.bat
```

Artifacts:

```text
dist\CamfrogStatusChanger.exe
dist\release-manifest.json
```

## Verification boundary

A successful local control update or successful PyInstaller build does not prove server-visible publication. Production readiness still requires independent-session verification on the exact supported Camfrog build.
