# Implementation Checklist

## Application baseline

- [x] Application namespace under `apps/camfrog-status-changer/`.
- [x] Pinned Python dependencies.
- [x] Atomic config recovery behavior.
- [x] Single-instance design.
- [x] Rotating logs.
- [x] Windowed/no-console build design.

## Camfrog discovery and targeting

- [x] Prefer `%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe`.
- [x] Fall back to running-process and legacy install paths.
- [x] Resolve main HWND by process/PID before title heuristics.
- [x] Known-binary SHA-256 profile and class anchors.
- [x] Unknown binaries fail closed; do not invoke hard-coded internal RVAs.

## Status semantics

- [x] Four independent message slots.
- [x] One tick applies exactly one message.
- [x] Sequential/random selection.
- [x] Seconds/minutes/hours interval units.
- [x] No immediate multi-message burst on Start.
- [x] Background-only and foreground-fallback are mutually exclusive.
- [ ] Independent account/session confirms server-visible publication.

## UI

- [x] TH/EN behavior for primary controls/dialogs.
- [x] Ctrl+C/V/X/A without duplicate paste.
- [x] History dialogs show real values instead of registry paths.
- [x] Technical details stay in logs/diagnostics.
- [ ] Keyboard-only navigation review.
- [ ] High-DPI scaling verification.

## History/local data

- [x] Read-only registry/history access.
- [x] REG_BINARY string carving.
- [x] Garbage/e-mail/hash/sensitive-name filtering.
- [x] Explicit History -> Presets import.
- [ ] Validate against additional Camfrog versions/profiles.

## Safe automation

- [x] Bounded Win32 messaging.
- [x] No generic button click guesses.
- [x] Only positively identified `CButtonStatusTS` is eligible for native button commit fallback.
- [x] UI read-back is not treated as server-publication proof.
- [ ] Dynamic-trace actual publish path.

## Styles

- [x] Marquee = one transformed text frame per tick.
- [x] No leading-space dependency.
- [x] Unsupported color markup is not advertised.
- [x] Random color uses visible Unicode markers only.
- [x] Static RE documents `CSPacket020401.text_status` as plain string.
- [ ] Add true color only if runtime/protocol evidence proves support.

## Production acceptance

Production-ready remains **false** until all applicable P0 items are verified with timestamped Windows/Camfrog evidence.
