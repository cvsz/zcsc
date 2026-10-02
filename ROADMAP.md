# Roadmap

ZeaZDev-CamfrogStatusChanger is the project name; Camfrog Status Changer is its Windows desktop application, maintained at the repository root. The repo also retains shared engineering tools.

## Application baseline

- [x] Manual status entry with a separate stage-only path
- [x] TH/EN standard status catalog and editable presets
- [x] Sequential/random one-message-per-tick rotation and marquee frames
- [x] Optional auto reply, room phrase notifications, room commands, and bad-word moderation
- [x] Read-only Camfrog profile/history discovery and diagnostics
- [x] Windows executable workflow with SHA-256 manifest artifact
- [x] Root-level reverse-engineering and multi-account isolation notes

`[x]` means implementation exists in source. It does not prove Camfrog server acceptance or live room permissions.

## Remaining application gates

- [ ] Verify status publication and background behavior on supported Windows/Camfrog builds; see [production readiness](PRODUCTION-READINESS.md).
- [ ] Keep Text Over Video inspection read-only until its control selectors and persisted value formats are verified.
- [ ] Review the proposed UAB integration's pinned source, license, and loopback API behavior before any installer implementation.
- [ ] Keep any room automation disabled until its exact room, UIA selectors, command syntax, and authorization are verified by the operator.

## Repository foundation

- [x] Security, contribution, governance, and release policies
- [x] Least-privilege baseline CI and security workflows
- [x] Local application-structure and documentation-link validation
- [x] GitHub administration verification helper
- [x] ZEAZ cross-agent execution framework and reusable AI playbooks
- [x] Skill, component, and plugin catalogs
