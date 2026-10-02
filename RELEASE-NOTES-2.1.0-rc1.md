# Camfrog Status Changer 2.1.0-rc1

## Native integration update

- Adds a version-gated native profile for the supplied Camfrog x64 binary (SHA-256 `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`).
- Native UI targeting now prioritizes `CComboBoxTS` even when UI Automation exposes it with an unexpected control type.
- Commit scoring prioritizes `CButtonStatusTS` discovered during static reverse engineering.
- Adds safe native diagnostics with known status-related RVAs and native class matches.
- Unknown Camfrog binaries automatically use the generic UI/Win32 integration path.
- Internal RVAs are diagnostic-only; direct function invocation remains disabled until dynamic ABI/call-chain verification is available.
- Tightens registry status sanitization to reject short REG_BINARY garbage, account identifiers, numeric state, hashes, and opaque tokens.
- Release manifest now records the application version and native-profile safety mode.

## Verified in this build environment

- `pytest`: 19 passed
- Python compile check: PASS
- Source package integrity: PASS

## Windows E2E gate still required

1. Build with `build_exe_fixed.bat`.
2. Open Camfrog and click `Detect` then `Native profile`.
3. Confirm known profile match for the supplied Camfrog EXE.
4. Test `Apply now` with rotation disabled.
5. Confirm status visibility from another Camfrog account/device.
6. Repeat while Camfrog is minimized.
7. Run `py diagnose_camfrog.py` if commit is not server-visible.
