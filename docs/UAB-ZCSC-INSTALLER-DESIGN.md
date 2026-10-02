# UAB + zcsc Installer Design

**Status:** Proposed design only. No UAB installation, MCP registration, network exposure, or Camfrog UI action has been performed.

## Goal

Provide an optional, reversible installer for the Camfrog Status Changer app that installs a pinned Universal App Bridge (UAB) sidecar and connects a narrowly scoped zcsc adapter to it. The first use case is UI inspection and a no-commit status-field probe on the Windows desktop where Camfrog is running.

The optional installer belongs under the repository-root `installer/` directory. Keep UAB decoupled from the Camfrog Status Changer executable and do not bundle or silently install it as part of the app.

## Evidence and constraints

- UAB documents a generic Win-UIA fallback and desktop MCP operations. Its supported-applications document describes a Windows 10/11 test environment but does not list Camfrog as tested.
- UAB's package metadata reports version 1.3.1, while its supported-applications test-environment section says 1.0.0; validate release-specific evidence instead of assuming the older test results apply to the current package.
- UAB documents a Node.js 18+ requirement. Its repository declares BSL-1.1; the installer must show and preserve the applicable license and must not describe UAB as MIT/open-source or redistribute it without confirming the grant permits that use.
- UAB's installer documentation describes additional effects such as an auto-starting service/task, browser extension, agent skill files, and API-key creation. These are broader than this integration needs.
- UAB's network documentation is inconsistent: it describes localhost-only operation while also documenting an HTTP server bound to `0.0.0.0`. The zcsc integration must explicitly bind loopback and must not open firewall ports.
- The current Camfrog app has a separate **Stage only (no Enter)** path. Its normal send path remains the only status commit path; a local UI text readback is not proof of server acceptance.

Sources: [UAB README](https://github.com/myles1663/UAB), [supported applications](https://github.com/myles1663/UAB/blob/main/SUPPORTED_APPLICATIONS.md), [UAB security policy](https://github.com/myles1663/UAB/blob/main/SECURITY.md), [UAB license](https://github.com/myles1663/UAB/blob/main/LICENSE), [Camfrog app README](../README.md), and [production readiness gates](../PRODUCTION-READINESS.md).

## Architecture decision

Treat UAB as an optional desktop-sidecar, not as a library imported by the Camfrog app.

```text
Codex / zcsc
    │
    │ narrow zcsc adapter (stdio MCP)
    ▼
UAB REST API on 127.0.0.1 (API key required for POST)
    │
    ▼
UAB Win-UIA backend in the signed-in Windows desktop session
    │
    ▼
Camfrog Video Chat.exe
```

For a co-located Codex and Camfrog installation, the adapter talks to the UAB loopback API directly. For a split host (for example, zcsc on Linux and Camfrog on Windows), remote connectivity is a separate prerequisite: use only an already-approved authenticated tunnel and keep UAB bound to loopback on Windows. The installer must not expose UAB directly to the LAN or Internet. If no approved tunnel is available, report the split-host mode as `BLOCKED`; do not widen the bind address or add firewall rules.

The zcsc adapter must not expose UAB's general desktop tools. Its initial allowlist is limited to:

1. `bridge_status`: version, health, and redacted connection state.
2. `inspect_camfrog_status`: identify the exact Camfrog process by executable path and inspect sanitized status-control metadata.

No text write, generic click, arbitrary key, room command, chat send, window-close, or process-termination operation is exposed through the initial zcsc adapter. It rejects unknown tool names, PIDs, control IDs, and action values.

## Installer interface

Implement a PowerShell entry point under `installer/` only after this design is approved. The install has two sides because UAB must run where the interactive Camfrog desktop exists, while zcsc/Codex may run on another host.

```powershell
.\installer\install-uab.ps1 -Plan
.\installer\install-uab.ps1 -Install -AcceptUabLicense
.\installer\install-uab.ps1 -Status
.\installer\install-uab.ps1 -TestNoCommit
.\installer\install-uab.ps1 -Uninstall
```

The Windows script manages only the desktop-side UAB process. A separate zcsc-side setup step registers the narrow MCP adapter with the Codex instance that will call it. If Codex is on a different host, zcsc must use an already-approved tunnel to reach the Windows loopback listener; the Windows script must not attempt remote Codex configuration or invent remote access credentials.

`-Plan` is the default and performs no writes, installs, MCP changes, firewall changes, or Camfrog actions. Mutating operations require an explicit flag. Commands are idempotent and return a nonzero exit code for failed prerequisites or verification.

### Preflight

- Require supported 64-bit Windows, the intended interactive user session, and a writable per-user install location. Do not request elevation for the initial design.
- Detect an existing UAB installation and report its version and owner. Never take over or upgrade an installation not created by this installer without an explicit choice.
- Require a reviewed, immutable UAB version/source revision and SHA-256 manifest. Never fetch the moving `main` branch. Verify the download before extraction and fail closed on mismatch.
- Detect Node.js 18+; if absent, show the pinned runtime and request explicit consent before a per-user install. Do not modify machine PATH or install a Windows service.
- Display the UAB BSL-1.1 terms and require an affirmative license acknowledgement. Do not infer acceptance from the repository URL.
- Show the exact directories, processes, MCP entry, and optional runtime that `-Install` will create. Redact keys from all output.

### Install and start

- Store versioned UAB files under `%LOCALAPPDATA%\ZCSC\UAB\versions\<version>` and generated configuration under `%LOCALAPPDATA%\ZCSC\UAB\`.
- Prefer the UAB CLI/server directly in an installer-owned, on-demand process. Do not run the upstream all-in-one installer unless a later audit proves its unrelated effects can be disabled. In particular, do not silently install the browser extension, write agent skill files, set global environment variables, or create an auto-start task.
- Bind the UAB API to `127.0.0.1`; require the generated API key for every mutating request. Keep the key in Windows Credential Manager or a user-only ACL-protected secret file. Never place it in the repo, Codex config, command-line arguments, logs, or test output.
- On a co-located setup only, optionally configure Codex through an installer-owned, removable MCP entry for the narrow zcsc adapter. Back up the existing user config, preserve unrelated server entries, and verify the effective entry with `codex mcp list`/`codex mcp get`. If safe merge/readback is unavailable, stop and print manual instructions rather than overwrite the config.
- On a split-host setup, leave Codex configuration untouched on Windows. The zcsc-side setup step configures the local stdio adapter to use the tunnel's loopback endpoint and retrieves the API key from that host's secret store.
- Start only the UAB process recorded by the installer. Default to on-demand start; do not add automatic startup unless the user separately opts in.

### No-commit verification

`-TestNoCommit` is read-only: it runs health and control discovery, requires one unambiguous Camfrog process and one status Edit, and returns sanitized control metadata. It performs no text write, keyboard input, click, or commit. Logs contain only pass/fail, duration, process identity hash, and sanitized control metadata—not status contents, chat text, or the API key.

For a write-path check, the operator separately uses the app's existing **Stage only (no Enter)** action. It clipboard-pastes the selected status, verifies the Edit readback, and deliberately leaves that text as an unsent draft. A failed write does not send Enter. The normal **Send to Camfrog** path remains unchanged and is never invoked by installer tests. This staged draft is a local UI result, not proof of server acceptance.

## Threat model and controls

| Threat | Control |
|---|---|
| Wrong process or spoofed Camfrog window | Match the executable path and process identity; require exactly one target and a unique expected Edit class/control. Fail closed on ambiguity. |
| Accidental status/chat/room action | Expose only the three allowlisted operations above; the installer test never presses Enter or invokes a send control. |
| Unrelated UI/chat data disclosure | Filter UIA results to the selected Camfrog process and status controls before returning data to zcsc; do not persist raw UI trees. |
| Remote desktop-control exposure | Loopback bind, API-key authentication, no firewall changes, no direct LAN/Internet listener; remote mode requires a pre-approved tunnel. |
| Dependency substitution or supply-chain change | Pin UAB revision, Node runtime, and dependency lockfile; verify hashes; review scripts and dependency advisories; no dynamic update from `main`. |
| Secret/config loss | Keep keys outside the repo, back up user MCP config before a scoped merge, verify readback, and remove only the installer-owned entry on rollback. |
| Uninstall damages existing state | Track ownership and exact created paths/PIDs. Never remove pre-existing UAB, Node.js, Camfrog data, or unrelated Codex configuration. |

## Update and rollback

- Install new UAB versions side by side; switch the active version only after health checks pass. Retain the previous version until the operator confirms the new one works.
- `-Uninstall` stops only the recorded UAB process, removes the installer-owned MCP entry and files after verifying every target is beneath the installer root, and restores the pre-install config backup only when no later user changes would be lost.
- Never stop Camfrog, clear its draft, edit its registry, or remove a user-managed UAB installation during rollback.

## Implementation plan and acceptance criteria

### Phase 1: Supply-chain and API proof

- [ ] Select a UAB release/revision allowed by the intended use and record its license, SHA-256, Node version, and dependency lockfile.
- [ ] Verify a loopback-only UAB server can expose read-only UIA details for the running Camfrog process on the target Windows build.
- [ ] Prove the adapter can identify the unique status Edit without returning unrelated application/chat data.

### Checkpoint 1

- [ ] No source is fetched from a moving branch; hash and license gates fail closed.
- [ ] UAB is not yet allowed to type, press keys, invoke controls, or change any Camfrog state.

### Phase 2: Installer and narrow adapter

- [ ] Implement dry-run, install, status, no-commit test, and uninstall with idempotent, ownership-tracked behavior.
- [ ] Implement and test only the two read-only adapter operations.
- [ ] Verify config merging preserves unrelated Codex MCP entries and stores no secret in the repo.

### Checkpoint 2

- [ ] PowerShell/Pester tests prove dry-run has no writes, hash mismatch aborts, license refusal aborts, and uninstall preserves pre-existing files/configuration.
- [ ] The adapter rejects arbitrary PIDs, control IDs, keypresses, and actions.

### Phase 3: Controlled Windows integration

- [ ] On Windows with the matching Camfrog build, verify read-only discovery, then separately use **Stage only (no Enter)** to verify clipboard paste and exact Edit readback.
- [ ] Confirm the Stage-only action sends no Enter and leaves the selected status as an unsent draft.
- [ ] Verify an explicit ordinary app send still follows its existing single-Enter commit path; independently check server-visible status only in an authorized controlled test.
- [ ] Record installer version, UAB revision/hash, Windows/Camfrog versions, test time, and sanitized results.

## Open gates

- Deployment topology is not confirmed: same-host stdio MCP or split-host via an approved tunnel.
- UAB's precise redistribution rights and the intended personal/commercial use must be resolved before packaging or distributing it.
- UAB's generic Win-UIA fallback is documented, but Camfrog control discovery and status-edit support remain unverified.
- UAB API bind defaults and the conflicting network descriptions must be tested against the pinned revision before enabling the server.

Until these gates pass, classify the installer as a proposal, not an installed bridge or working Camfrog integration.
