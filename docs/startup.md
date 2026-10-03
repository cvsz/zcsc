# Set up Camfrog Status Changer

Camfrog Status Changer is a Windows desktop application for user-managed Camfrog status presets and optional UI automation. The application does not verify that Camfrog or its server accepted a submitted status or room command.

## Requirements

- Windows 10 or 11
- Python 3.12 for development, or the packaged executable from a trusted workflow artifact
- A locally installed Camfrog client for interactive integration

## Run from source

In PowerShell, from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-build.lock
.\run_dev.bat
```

The app stores its settings at `%APPDATA%\CamfrogStatusChanger\config.json` on Windows, or `~/.config/CamfrogStatusChanger/config.json` when `APPDATA` is unset. Logs normally go to `%APPDATA%\CamfrogStatusChanger\logs\app.log`; if that location cannot be opened, the app falls back to `%TEMP%\CamfrogStatusChanger\logs\app.log`. Review local settings and logs before sharing them; they may contain personal status text, nicknames, room names, or UI selectors.

If a valid JSON config has values in an unexpected shape, the app backs it up and recovers with safe defaults. Config saves use an atomic temporary file and retry a short-lived Windows file lock; if all retries fail, the prior config is kept and the temporary file may remain for recovery.

## Build and validate

```powershell
python -m pytest -q
python -m compileall -q app.py automation camfrog system ui scripts version.py self_test.py
.\build_exe.bat
```

The Windows workflow and local batch entrypoints run `scripts/build_windows.py`, which installs the hash-locked build dependencies, runs tests and compile checks, builds the executable in isolated staging directories, verifies the SHA-256 manifest, and publishes the EXE/manifest pair to `dist/`. The workflow uploads a temporary artifact. Build outputs are not committed to Git.

On POSIX development hosts, use `python3 -m pytest -q`, `python3 -m compileall ...`, and `make validate-repo`. The executable build requires Windows.

## First interactive run

1. Start Camfrog and sign in through its own UI.
2. Launch Camfrog Status Changer and use **Setup** to select or detect the Camfrog executable.
3. Configure status text or UI Automation selectors only for controls you have inspected on your Camfrog build.
4. Keep room actions and moderation disabled until the room, selectors, syntax, and permissions have been verified in a controlled test room.
5. Test status submission with a harmless value. A local UI write and Enter dispatch do not prove server-visible publication.

Camfrog's UI and internal control behavior may change between client versions. Unknown controls must not be guessed; the status integration requires a positively identified control or an explicit configured automation ID.

Automatic detection checks the supported per-user Camfrog install location, then known client executable names and legacy Program Files locations. If more than one window matches the selected client, close the extra client windows or select the intended executable; automation stops instead of guessing which account to control.

## Configuration and security

- Do not store Camfrog passwords, session tokens, or browser cookies in this application or repository.
- Keep user-specific settings, logs, screenshots, and Camfrog profile data out of commits and issue reports.
- Review the application [security policy](../SECURITY.md) and [production-readiness gates](../PRODUCTION-READINESS.md) before distributing a build.
