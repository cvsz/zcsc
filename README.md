# ZeaZDev-CamfrogStatusChanger

Camfrog Status Changer is a Windows desktop companion for managing custom-status text and optional automation through Camfrog's visible UI. The source version is `2.2.5-rc13`; this version label does not certify a packaged, signed, or server-verified release. See [production readiness](PRODUCTION-READINESS.md) for the remaining Windows and Camfrog checks.

## Features

- Edit four independent status values and choose from 50 Thai/English standard statuses.
- Read Camfrog Status History without writing to the Camfrog Registry; select history rows for random rotation or explicitly import them into presets.
- Run sequential or randomized one-row-at-a-time rotation with schedules and a minimum send interval.
- Emulate marquee by submitting changing status text. This is repeated status submission, not a native Camfrog animation; server rendering is unverified.
- Optionally monitor configured visible chat controls for auto-reply, room phrases, or moderation. These actions are disabled by default and stop when the target or visible history is ambiguous.
- Open public Camfrog profile links in the default browser without collecting credentials or browser cookies.
- Inspect selected Camfrog UI metadata using a read-only diagnostic path.

ZCSC now binds each active automation session to one verified Camfrog PID. It can launch Camfrog, capture the resulting PID, or explicitly bind an already-running verified PID. All status/chat/room UI discovery is restricted to that PID; if the PID exits, the session disconnects instead of silently switching to another Camfrog process. This is PID isolation, not full account/profile sandbox isolation.

## Install and run

For Windows requirements, source setup, validation, and build steps, follow [docs/startup.md](docs/startup.md). For a source checkout, run `run_dev.bat` from PowerShell at the repository root. Executable builds are produced by the Windows workflow and are not committed to this repository. The workflow verifies the release manifest and PE32+ x64 format, scans the built EXE with Microsoft Defender, and uploads those verification records with the candidate artifact.

## Security model

- Sign in through Camfrog itself. Do not store Camfrog passwords, session tokens, or browser cookies in this app or repository.
- Status and room actions use visible UI Automation or Win32 controls. Internal Camfrog RVAs are diagnostic-only and are not invoked.
- Room commands and moderation require explicit configuration. Automatic moderation remains off by default; manual room commands require confirmation. UI submission does not prove server authorization or acceptance.
- Registry discovery is read-only and skips sensitive keys. Registry-history dumps and local config/log files can contain personal status text, nicknames, room names, or selectors. Do not share them. The optional `--redact` mode is partial and cannot guarantee anonymization.
- Do not add antivirus exclusions to make an artifact run. Review the [security policy](SECURITY.md) and scan the final artifact.

## Repository history and reverse engineering

The working source no longer carries the legacy account-specific release bundles, but those blobs remain in Git history. The path-only findings and the unexecuted rewrite procedure are in [the history scan report](docs/operations/history-pii-scan-report.md) and [rewrite runbook](docs/operations/history-pii-rewrite-runbook.md). Reverse-engineering notes are in [docs/reverse-engineering](docs/reverse-engineering/); EULA/legal review is pending before redistribution.

## Project guidance

- [Changelog](CHANGELOG.md)
- [Agent contract](AGENTS.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Roadmap](ROADMAP.md)
- [Production readiness](PRODUCTION-READINESS.md)
- [RC13 final release runbook](docs/operations/rc13-final-release-runbook.md)
- [Development and startup guide](docs/startup.md)
- [Architecture](docs/architecture.md)
- [AI playbooks](docs/ai/README.md)
