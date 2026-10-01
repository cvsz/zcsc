# Roadmap

## P0 — Release gate

- [x] Integrate current application design and core modules.
- [x] One-message-per-tick scheduler semantics.
- [x] Background-only / foreground-fallback mutual exclusion.
- [x] Safe button targeting; no generic `CButtonTS` guessing.
- [x] Readable TH/EN dialogs/history values.
- [x] Clipboard double-paste fix.
- [x] Build isolation and release hash manifest design.
- [ ] Verify manual status change end-to-end on Windows using the target Camfrog build.
- [ ] Verify the changed status from an independent Camfrog session/account.
- [ ] Verify 10+ rotation intervals without duplicate/multi-message ticks.
- [ ] Verify minimized/background-only publication.
- [ ] Capture timestamped logs/evidence for the exact executable hash.

## P1 — Native integration confidence

- [x] Static native profile for the analyzed Camfrog x64 binary.
- [x] Identify native classes/resource anchors and status-related RTTI/protobuf anchors.
- [x] Reverse-engineer `CSPacket020401.text_status` as protobuf field #2/string.
- [x] Map Text Over Video `TOV_*` settings and controls.
- [ ] Runtime-trace `Messages::ChangeStatus -> SetSelfStatus -> CSPacket020401`.
- [ ] Map field #1/#3 semantics through differential tracing.
- [ ] Confirm exact internal commit event/owner path without arbitrary RVA invocation.

## P1 — Product quality

- [ ] Signed Windows release pipeline.
- [ ] Windows VM GUI/E2E smoke tests.
- [ ] Automatic redacted diagnostic bundle.
- [ ] Compatibility check for unknown Camfrog versions.
- [ ] Installer/uninstaller with startup-registry cleanup.

## P2 — Optional

- [ ] User-configurable marquee separator/direction/width.
- [ ] Per-message scheduling windows.
- [ ] Text Over Video control only after storage/runtime semantics are verified.
- [ ] True custom-status color only if protocol/runtime evidence proves support.
