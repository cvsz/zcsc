# Git history sensitive-data rewrite runbook

## Authorization gate

This runbook is preparation only. Do not rewrite history, force-push, merge, or publish a replacement artifact until the repository owner explicitly authorizes the exact target repository and refs. No rewrite has been run for this audit.

The current checkout contains unrelated in-progress P1–P6 edits. Never run a history rewrite in it. Use a new isolated mirror clone after approval and coordinate a repository-wide push freeze first.

## Preparation

1. Confirm the repository owner, target URL, visibility, retention requirements, and approved maintenance window. Record all branch, tag, and pull-request refs. Coordinate the open dependency PRs and all collaborators before the window.
2. Create an encrypted, access-restricted mirror backup outside the working checkout. The backup will retain the sensitive history and must not be uploaded to ordinary CI, shared storage, or a public location.
3. Create a fresh mirror clone in a dedicated temporary directory. Verify its remote and ref inventory. The installed `git-filter-repo` documents `--sensitive-data-removal` as fetching refs from the origin; it can discard local changes, which is why this must be a fresh clone with no local work.
4. From the path-only [scan report](history-pii-scan-report.md), create a private `paths-to-remove.txt` containing the 12 affected historical ZIP paths. Do not add the report's nested `!member` paths; Git filters the containing ZIP blob.
5. Obtain the exact replacement literals through an authorized, local source. Create a restricted `replacements.txt` outside the repository with one `literal:OLD==>[REDACTED]` entry per value. Do not print, commit, attach, or place those values in issue/PR text, command history, shell tracing, or CI logs. If any value cannot be confirmed, stop and request owner review rather than guessing.
6. Review both private filter files and the exact target refs with a second maintainer. Preserve current source files; replace their sensitive literals rather than removing whole source files. Remove only the affected historical ZIP paths identified in the scan report.

The ZIP path entries for `paths-to-remove.txt` are:

```text
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.0.0-rc1-production-candidate.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.0-rc1-native-profile.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.1-rc2-safe-commit.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.2-rc3-fallback-toggle-fix.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.0-rc2-merged.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.3-rc5-message-focus-fix.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.3.1-rc2-merged-all.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.4-window-detection-fix.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.6-registry-reader.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.7-hidden-cmd-active-intervals.zip
apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.8-registry-deep-scan.zip
```

## Dry-run in a disposable mirror clone

After authorization, run the prepared command only in the disposable mirror clone. Do not use `--partial`, `--no-fetch`, or `--force`; stop if `git-filter-repo` refuses the clone or reports refs not covered by the inventory.

```sh
git filter-repo \
  --sensitive-data-removal \
  --replace-text "$REPLACEMENTS_FILE" \
  --paths-from-file "$PATHS_TO_REMOVE_FILE" \
  --invert-paths
```

Before publishing, inspect the generated commit/ref mapping and changed-ref report. Re-run the same identity/contact scan over every rewritten ref, recursively inspect remaining archives and bytecode, verify removed literals are absent, and run `git fsck --full`. A remaining match or incomplete ref inventory is a stop condition. The path-only report itself is not sufficient to authorize a rewrite.

## Coordinated publication and cleanup

1. Obtain a second maintainer's written approval of the rewritten commit map, branch/tag inventory, scan results, and rollback plan.
2. Push only the explicitly approved rewritten branch and tag refs using reviewed per-ref commands. Do not use `git push --mirror` against GitHub; GitHub-managed pull refs are not ordinary writable branches. Do not overwrite a ref that changed during the freeze.
3. Ask GitHub Support to purge cached views and affected pull-request references where needed. Review open PRs, forks, releases, Actions artifacts/logs/caches, and collaborator clones; recreate or refresh them from rewritten refs as directed by the repository owner.
4. Require collaborators to make fresh clones or carefully reset to the rewritten refs. Old clones, forks, backups, and exported archives can reintroduce the removed data.
5. Keep the restricted backup until the owner approves its destruction and the external cache cleanup is verified. Record verification results without recording the sensitive values.

## Rollback boundary

Do not restore old refs into the rewritten hosted repository after publication; doing so would reintroduce the sensitive history. The restricted mirror is a recovery source only under a new explicit owner decision and a reviewed plan.
