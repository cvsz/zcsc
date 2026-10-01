# Changelog

## [Unreleased]

### Fixed — runtime follow-up

- Wired the existing **Allow foreground fallback** UI option into the controller instead of failing immediately after background verification fails.
- Added explicit foreground fallback flow: restore/focus Camfrog, use configured relative status target, replace one message, press Enter, and restore minimized state.
- Added status-change stages to error reporting so dialogs identify whether failure occurred at validation, rate limit, background verification, foreground fallback, or runtime exception.
- Normalized Camfrog executable paths to Windows backslash form for Detect, Browse, load, and save.
- Initialized COM in STA mode before loading the UI/controller stack to avoid pywinauto/comtypes apartment-mode churn.
- Reduced Windows PyInstaller warning noise by excluding unused Linux/macOS tray/UI backends while keeping Win32 tray support explicit.

### Integrated — 2026-10-01

- Integrated Camfrog Status Changer `2.3.1-rc2` project documentation and core application modules.
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
