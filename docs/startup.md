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
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest pyinstaller==6.22.3
.\run_dev.bat
```

The app stores its settings at `%APPDATA%\CamfrogStatusChanger\config.json` on Windows, or `~/.config/CamfrogStatusChanger/config.json` when `APPDATA` is unset. Review local settings and logs before sharing them; they may contain personal status text, nicknames, room names, or UI selectors.

## Build and validate

```powershell
python -m pytest -q
python -m compileall -q app.py automation camfrog system ui version.py self_test.py
.\build_exe.bat
```

The Windows workflow also runs the tests, builds the executable, creates a SHA-256 manifest, and uploads a temporary artifact. Build outputs are not committed to Git.

On POSIX development hosts, use `python3 -m pytest -q`, `python3 -m compileall ...`, and `make validate-repo`. The executable build requires Windows.

## First interactive run

1. Start Camfrog and sign in through its own UI.
2. Launch Camfrog Status Changer and use **Setup** to select or detect the Camfrog executable.
3. Configure status text or UI Automation selectors only for controls you have inspected on your Camfrog build.
4. Keep room actions and moderation disabled until the room, selectors, syntax, and permissions have been verified in a controlled test room.
5. Test status submission with a harmless value. A local UI write and Enter dispatch do not prove server-visible publication.

Camfrog's UI and internal control behavior may change between client versions. Unknown controls must not be guessed; the status integration requires a positively identified control or an explicit configured automation ID.

## Configuration and security

- Do not store Camfrog passwords, session tokens, or browser cookies in this application or repository.
- Keep user-specific settings, logs, screenshots, and Camfrog profile data out of commits and issue reports.
- Review the application [security policy](../SECURITY.md) and [production-readiness gates](../PRODUCTION-READINESS.md) before distributing a build.
