# Architecture

ZeaZDev-CamfrogStatusChanger is the project; Camfrog Status Changer is its Windows desktop application. Its source, tests, build assets, and application documentation live at the repository root.

## Application layers

### Dashboard and entry point

- `app.py` initializes the desktop app.
- `ui/dashboard.py` provides the feature-oriented UI and settings controls.
- `automation/` manages status rotation, scheduling, and marquee frames.

### Camfrog integration

- `camfrog/controller.py` coordinates status updates and guardrails.
- `camfrog/detector.py` and the UIA/Win32 helpers target the running Camfrog desktop client.
- `camfrog/registry_status.py` and related readers provide read-only profile/history discovery.
- `camfrog/native_profile.py` uses version-gated class/fingerprint evidence; diagnostic RVAs are not invoked.

The integration is desktop-UI based. A verified local Unicode paste and Enter dispatch do not independently prove server publication. Room commands, auto reply, and bad-word actions require explicit configuration and remain disabled by default.

### Local state and system integration

- `system/config_store.py` stores application configuration under the current user's application-data directory and handles recovery from malformed files.
- `system/logging_setup.py`, `system/tray.py`, `system/startup.py`, and `system/single_instance.py` handle logs and Windows desktop lifecycle behavior.
- `app.ico` and `bad_word_starters.json` are packaged as runtime resources by the Windows build.

## Repository tooling

The root also retains zcsc governance, CI, repository validation, GitHub administration, and AI-agent guidance. These tools support the application but are not part of the Camfrog runtime. See [development](development.md), [release](release.md), and the root [agent contract](../AGENTS.md).

## Build and evidence boundary

The Windows workflow runs the application tests and compile check, builds a one-file executable, generates a SHA-256 manifest, and uploads a temporary workflow artifact. Local ignored `build/` and `dist/` directories may contain historical Camfrog and application artifacts; build scripts must use the app-specific work directory and preserve unrelated files.

Passing repository or application checks does not prove server-visible status changes, room permissions, signing, antivirus reputation, or production readiness. See [production readiness](../PRODUCTION-READINESS.md).
