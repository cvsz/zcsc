# Release

## Required evidence before production release

- exact Camfrog executable hash recorded
- application tests green on release head
- Windows build completes from clean checkout
- SHA-256 manifest matches published executable
- manual status publication visible from an independent Camfrog session/account
- 10+ rotation intervals execute with one message per tick
- minimized/background-only behavior verified
- startup/tray/single-instance behavior verified
- Defender/SmartScreen behavior reviewed
- production artifact code-signed

Do not label a release production-ready from unit tests or local-control read-back alone.
