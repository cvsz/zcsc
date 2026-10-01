# Security Policy

## Scope

`zcsc` controls a locally running Camfrog client on Windows. Treat the Camfrog process, local profile storage and reverse-engineering artifacts as security-sensitive surfaces.

## Reporting

Do not publish exploitable vulnerabilities, credentials, tokens, cookies, session material, private profile data or raw memory dumps in public issues. Use GitHub private vulnerability reporting/security advisories when available.

## Security invariants

- Never request or store the user's Camfrog password.
- Registry/history discovery is read-only.
- Diagnostics avoid credential/session/token/cookie values.
- Unknown Camfrog binaries must not receive hard-coded internal function calls.
- Internal RVA anchors are research evidence until ABI/call-path behavior is runtime verified.
- Win32 messaging is bounded by timeouts.
- Generic Camfrog buttons are never clicked as commit guesses.
- Foreground fallback is explicit and mutually exclusive with background-only mode.
- Antivirus exclusions, privilege bypasses and credential extraction are not normal setup steps.

## Reverse-engineering boundaries

Reverse engineering here is for interoperability, diagnostics and controlled testing. It must not be extended to authentication bypass, account takeover, credential/session extraction, covert persistence, or hidden remote control.

## Release security

Production distribution should use code signing, verify the final SHA-256 manifest, review dependency/security alerts, and test the exact signed executable with Windows Defender/SmartScreen. Passing unit tests alone is not production evidence.
