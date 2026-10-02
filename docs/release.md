# Release

## Scope

The Windows application workflow and local batch entrypoints use `scripts/build_windows.py` as the single test/build/manifest implementation. It installs `requirements-build.lock` with `--require-hashes`, audits the lock, runs tests and compile checks, builds into isolated staging directories, verifies the manifest against the staged executable, then publishes the EXE and manifest to `dist/`. CI uploads the executable and manifest as a short-lived workflow artifact. The Ubuntu workflow also uploads a JUnit test report. These workflows do not publish a GitHub Release, sign the executable, or establish production readiness.

## Versioning

The application version is maintained in `version.py` and recorded in `CHANGELOG.md`. Keep prerelease status explicit until a stable-release policy is adopted.

## Release checklist

1. Confirm the release commit is the intended exact head.
2. Ensure required CI/security checks pass on that exact head.
3. Confirm protected-branch/admin controls are effective.
4. Update `CHANGELOG.md` and compatibility/migration notes.
5. Verify deployment and rollback procedures.
6. Verify migrations and data rollback/forward strategy when applicable.
7. Verify required backup/restore evidence for stateful systems.
8. Create/push the release tag according to project policy.
9. Publish artifacts only from trusted workflows/environments.
10. Generate provenance/signing/attestation where required.
11. Verify the published artifact and deployed environment.
12. Record release evidence and remaining known risk separately.

## Production readiness

Release authorization and production readiness are distinct.

A maintainer may authorize a release with accepted risk, but accepted risk does not convert `PARTIALLY VERIFIED`, `UNVERIFIED`, or `BLOCKED` readiness gates into `VERIFIED`.

Use the canonical evidence definitions in `../ZEAZ-INTRODUCTION.md`.

## Rollback

Document and test, as appropriate:

- last known-good artifact/build
- application rollback
- safe database/data migration handling
- configuration rollback
- credential/artifact invalidation after compromise
- traffic/routing rollback
- operator and stakeholder communication

A rollback document without environment-appropriate execution evidence is not proof that recovery will work.
