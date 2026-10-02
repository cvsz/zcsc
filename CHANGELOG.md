# Changelog

## [Unreleased]

### Fixed — PR review follow-up

- Reject generic UIA ComboBoxes as Camfrog status targets unless an exact automation ID or observed status value identifies them. Refuse background and coordinate fallbacks when UIA exposes an unverified generic target.
- Keep the dashboard visible when the tray fails to start, restore it if the tray thread later stops, and exit on close rather than leaving an unreachable hidden process.
- Allow the first auto-reply, moderation alert, or room-event alert immediately after startup; begin cooldown checks only after a prior action has a timestamp.
- Isolate Windows platform test doubles to each Camfrog module instead of mutating shared `os.name`, preserving Python 3.12/POSIX test behavior.
- Remove project-template bootstrap and inventory files so this checkout consistently documents the Camfrog application at its root.
- Default Make targets to `python3` on POSIX and `py -3` on Windows; document that executable builds are temporary workflow artifacts, not checked-in files.

### Repository layout

- Promoted the Camfrog Status Changer application, tests, documentation, Windows build assets, and preserved local build artifacts from the former app subdirectory to the repository root.
- Consolidated its Windows test/build workflow at the root and retained the repository baseline workflow.
- Isolated PyInstaller work output under `build/CamfrogStatusChanger-work` so build scripts no longer remove the adjacent Camfrog analysis files in `build/`.
- Kept the complete test suite in the Ubuntu baseline workflow after the root migration; it now installs the app requirements and runs pytest rather than selecting only the bootstrap test.

### Fixed — runtime follow-up

- Wired the existing **Allow foreground fallback** UI option into the controller instead of failing immediately after background verification fails.
- Added explicit foreground fallback flow: restore/focus Camfrog, use configured relative status target, replace one message, press Enter, and restore minimized state.
- Added status-change stages to error reporting so dialogs identify whether failure occurred at validation, rate limit, background verification, foreground fallback, or runtime exception.
- Normalized Camfrog executable paths to Windows backslash form for Detect, Browse, load, and save.
- Initialized COM in STA mode before loading the UI/controller stack to avoid pywinauto/comtypes apartment-mode churn.
- Reduced Windows PyInstaller warning noise by excluding unused Linux/macOS tray/UI backends while keeping Win32 tray support explicit.

### Fixed — audit follow-up

- Restrict Camfrog discovery to known client executable names or the exact configured executable path, so the status manager itself is not mistaken for an online Camfrog client.
- Stop status/room automation when multiple Camfrog windows or status controls match instead of sending to the highest-scoring guess; the Win32 fallback now preserves the ambiguity result and does not continue to coordinate fallback.
- Remove account-specific status text, owner metadata, email addresses, and secret-like values from fresh defaults and test fixtures.
- Upgrade Pillow to the minimum fixed version reported by the dependency vulnerability audit.
- Pin PyInstaller to the version used for the verified Windows candidate builds.
- Route the standard build entrypoint through the tested Windows builder and keep the current app process and published EXE until staged tests and packaging succeed.
- Fix Inspect error callbacks that referenced the exception variable after its `except` scope ended.
- Add `scripts/__init__.py` so repository tests reliably import the local bootstrap module when an unrelated installed `scripts` package exists.
- Exclude legacy release ZIPs containing account-specific identity/contact data from the new root `tags/` directory; only the neutral reverse-engineering kits were carried forward.

### Integrated — 2026-10-01

- Imported the historical `2.3.1-rc2` source bundle and documentation. This archive label is not the current application version; `version.py` is authoritative.
- Added background-first controller, Win32/UIA integration, known-client fingerprint profile and fail-closed fallbacks.
- Added four independent message slots and enforced `1 tick = 1 message = 1 set_status()`.
- Added sequential/random rotation and seconds/minutes/hours interval selection.
- Added TH/EN UI behavior, readable alerts, tray/startup design and hidden-console build flow.
- Fixed duplicate Ctrl+V behavior caused by stacked Tk paste bindings.
- Added read-only registry/history discovery, binary string carving, garbage filtering and explicit import-to-presets flow.
- Blocked generic `CButtonTS` commit guessing after it activated unrelated Camfrog controls/browser actions during testing.
- Implemented marquee as text-frame updates rather than unsupported markup.
- Replaced unsupported custom-status color markup with visible Unicode color markers.
- Added config recovery, single-instance behavior, log rotation and release SHA-256 manifest design.
- Added RE findings for `CSPacket020401.text_status` and Text Over Video `TOV_*` settings.

### Evidence baseline

The prior integrated implementation package reported 41 passing tests. Repository CI must independently validate each committed revision.

### Still unverified

- server-visible custom-status publication on the supported Camfrog build
- minimized/background-only end-to-end publication across client updates
- code-signing/Defender/SmartScreen behavior of the final Windows artifact
