# Camfrog Status Changer

Version: **2.3.1-rc2**

This folder contains the Windows application integrated into `cvsz/zcsc`.

## Features

- four independent messages
- one tick = one message = one apply attempt
- seconds/minutes/hours intervals
- sequential/random rotation
- background-first safe native automation
- explicit foreground fallback
- TH/EN UI
- read-only status-history discovery
- Unicode color markers and text-frame marquee
- known Camfrog binary fingerprint profile
- safe user dialogs and technical logging
- PyInstaller windowed build and SHA-256 manifest

## Run

```powershell
py -m pip install -r requirements.txt
py app.py
```

## Build

```cmd
build_exe_fixed.bat
```

## Important limitation

A local UI/control update is not proof that Camfrog published the status to the service. Production readiness requires an independent Camfrog session/account to observe the changed status on the exact supported client build.
