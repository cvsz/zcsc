# Git history identity scan

## Scope and method

The offline scan covered 47 commits reachable from the checkout's `--all` refs, 369 distinct Git blobs, all 15 distinct ZIP blobs, and 639 recursively inspected ZIP members. It scanned raw binary content, nested ZIP members, and `.pyc` payloads. All 15 ZIP blobs were readable, with no archive read errors. `gitleaks` and `trufflehog` were unavailable, so a local literal-identity, contact-pattern, and high-confidence credential-pattern fallback was used. Detector values are intentionally not recorded here.

The contact-pattern pass found no formatted phone candidates. Email-shaped strings were confined to registry-redaction regression fixtures. The high-confidence credential-pattern pass found no private-key or common provider-token candidates. Identity-marker candidates were found in the source and bundled paths below. These locations corroborate the earlier audit observation about account-specific content in historical bundles; the scan report intentionally contains paths and commit IDs only. Pattern scans cannot prove that all personal data has been found.

## Direct blob paths

| Commit | Path |
| --- | --- |
| `3861d9ca131bd37b9d4bff1993ffb12ed6d32d95` | `apps/camfrog-status-changer/self_test.py` |
| `3d4a977c043b1322edcffece46a9176fc9f79ae1` | `apps/camfrog-status-changer/system/config_store.py` |
| `3d4a977c043b1322edcffece46a9176fc9f79ae1` | `apps/camfrog-status-changer/tests/test_status_styles.py` |
| `cac8bc4ddb0179b82af0d1c855faa71a149d4810` | `apps/camfrog-status-changer/tests/test_registry_binary_history.py` |
| `cac8bc4ddb0179b82af0d1c855faa71a149d4810` | `apps/camfrog-status-changer/tests/test_registry_garbage_filter.py` |
| `cac8bc4ddb0179b82af0d1c855faa71a149d4810` | `apps/camfrog-status-changer/tests/test_registry_sanitize.py` |
| `ffb92c118ea620a35996b87e07f67aeeff5b6d66` | `plugins.d/_defaults.yml` |

## Historical ZIP paths

| Commit | Path |
| --- | --- |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.0.0-rc1-production-candidate.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.0-rc1-native-profile.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.1-rc2-safe-commit.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.2-rc3-fallback-toggle-fix.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.0-rc2-merged.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.3-rc5-message-focus-fix.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.3.1-rc2-merged-all.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.4-window-detection-fix.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.6-registry-reader.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.7-hidden-cmd-active-intervals.zip` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.8-registry-deep-scan.zip` |

## Nested bytecode paths

| Commit | Path |
| --- | --- |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.2-rc3-fallback-toggle-fix.zip!camfrog-status-changer/system/__pycache__/config_store.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.2-rc3-fallback-toggle-fix.zip!camfrog-status-changer/tests/__pycache__/test_registry_garbage_filter.cpython-313-pytest-9.0.2.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.1.2-rc3-fallback-toggle-fix.zip!camfrog-status-changer/tests/__pycache__/test_registry_sanitize.cpython-313-pytest-9.0.2.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/system/__pycache__/config_store.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_binary_history.cpython-313-pytest-9.0.2.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_binary_history.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_garbage_filter.cpython-313-pytest-9.0.2.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_garbage_filter.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_sanitize.cpython-313-pytest-9.0.2.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-2.2.4-rc6-clipboard-fix.zip!cf_clipboard_fix/tests/__pycache__/test_registry_sanitize.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.6-registry-reader.zip!camfrog-status-changer/system/__pycache__/config_store.cpython-313.pyc` |
| `b11e95b181098f975c3a132d6316374c62cdc76b` | `apps/camfrog-status-changer/tags/CamfrogStatusChanger-v1.8-registry-deep-scan.zip!camfrog-status-changer/system/__pycache__/config_store.cpython-313.pyc` |
