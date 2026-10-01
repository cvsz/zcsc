# zcsc — Camfrog Status Changer

Windows desktop automation and reverse-engineering research workspace for safely changing Camfrog custom status text, rotating messages on a schedule, reading local status history, and documenting Camfrog client integration behavior.

> **Status:** `2.3.1-rc2` release candidate. Automated regression coverage exists, but server-visible Camfrog status publication still requires Windows/Camfrog end-to-end verification on the supported client build before this repository can be called production ready.

## Current capabilities

- Windows GUI using Python + CustomTkinter.
- Preferred Camfrog discovery at `%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe`, then running-process and legacy path fallbacks.
- Four independent message slots. **One interval tick = one message = one set_status() call.**
- Sequential/random rotation with seconds/minutes/hours intervals.
- Background-first native/UI automation with fail-closed behavior and explicit foreground fallback.
- Native profile fingerprinting for the analyzed Camfrog x64 build.
- Read-only custom-status history discovery and explicit import to presets.
- TH/EN UI mode, readable alerts, system tray, Windows startup, hidden-console executable build.
- Ctrl+C / Ctrl+V / Ctrl+X / Ctrl+A support without double-paste.
- Marquee implemented as one transformed text frame per interval; unsupported HTML/BBCode markup is not used.
- Random “color” mode uses visible Unicode markers only. Static RE of `CSPacket020401.text_status` found a plain-string field and no verified custom-status font-color field.
- Build hardening: tests before packaging, isolated staging, runtime icon bundling, SHA-256 release manifest.

## Repository layout

```text
apps/camfrog-status-changer/   Application core and app-specific documentation
docs/                          Architecture, development, release and research documentation
.github/                       CI, CodeQL, dependency review, issue/PR policy
scripts/                       ZEAZ repository governance helpers
```

## Quick start

```powershell
cd apps\camfrog-status-changer
py -m pip install -r requirements.txt
py app.py
```

Build:

```cmd
cd apps\camfrog-status-changer
build_exe_fixed.bat
```

## Verification baseline

```text
pytest:        41 passed
compile check: PASS
self-test:     PASS
```

These results validate covered code paths. They do **not** prove that a specific Camfrog client published a status to the Camfrog service.

## Reverse-engineering findings

- `CSPacket020401.text_status` is protobuf field #2, wire type 2/string.
- The analyzed parser recognizes tags `0x08`, `0x12`, and `0x18`; no verified custom-status color/marquee field was found in this packet.
- Text Over Video is a separate Camfrog feature with `TOV_*` settings including text/background colors, font, alignment and transparency.
- Native anchors include `CComboBoxTS`, `CEdit4ComboInnerTS`, `CButtonStatusTS`, `custom_status_combo`, and status RTTI/protobuf anchors.

Reverse engineering here is for interoperability, diagnostics and controlled testing. Do not use this repository to extract credentials, tokens, sessions, cookies, or private user data.

## Safety model

- Background-only and foreground-fallback are mutually exclusive.
- Generic Camfrog buttons such as `CButtonTS` are not clicked as commit guesses.
- Registry/history access is read-only and filters credential/session-like values.
- Internal RVAs are diagnostic anchors only until runtime verified.
- Technical details go to logs/diagnostics; user dialogs show readable TH/EN messages.

## Production status

See `IMPLEMENTATION-CHECKLIST.md`, `ROADMAP.md`, and `docs/release.md`.

MIT licensed. See `LICENSE`.
