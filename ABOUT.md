# About zcsc

`zcsc` is the Camfrog Status Changer project maintained under `cvsz` / ZEAZDEV.

It combines a Windows desktop utility with interoperability-focused reverse-engineering notes for the Camfrog client. The product provides user-controlled status-message rotation and diagnostics without storing Camfrog credentials or bypassing authentication.

## Product scope

- configurable custom-status messages
- one-message-per-interval rotation
- seconds/minutes/hours scheduling
- background-first Windows automation
- Camfrog executable/process discovery
- read-only local status-history import
- Thai/English UI
- tray/startup behavior
- safe diagnostics and release evidence
- reverse-engineering research for status and Text Over Video internals

## Explicit non-goals

- credential, token, cookie or session extraction
- authentication bypass
- hidden remote-control functionality
- undocumented server abuse or spam automation
- claiming unsupported custom-status color markup as a real protocol feature

## Evidence policy

Automated tests, static reverse engineering, local control read-back, dynamic tracing and independent server-visible verification are separate evidence levels. A release must not claim end-to-end publication until the final level is demonstrated on the exact supported Camfrog build.
