# Changelog

## [Unreleased]

### Fixed — P1 status styles and text

- Validate color templates using only one `{text}` placeholder and an optional `{color}` placeholder. Invalid templates now fall back to unstyled text, do not report an applied color, and show a localized warning in the status preview.
- Keep marquee windows on Unicode grapheme-like clusters, skip blank frames for nonblank statuses, and safely clamp invalid widths to the supported 4–80 range.
- Use the same validated hex-color palette for random color selection and status styling.
- Deprecate the legacy two-line composer while preserving every supplied row; status comparisons now remove NUL characters and normalize Unicode to NFC.
- Preserve the existing config schema; no migration is needed. Local validation passed 224 pytest tests, `compileall`, and `scripts/validate_repo.py`; Windows CI and live Camfrog behavior remain unverified.

### Fixed — P2 startup and config hardening

- Guard startup logging, config initialization/loading, single-instance checks, and UI import so early failures are logged and shown through a temporary Tk root that is always destroyed.
- Make startup language selection tolerate missing or wrong-shaped `ui` config values. Valid JSON with `ui: null`, a list, or another wrong shape is covered by recovery tests; existing `ConfigStore` backup-and-default recovery required no behavior change.
- Fall back from the application-data log path to `%TEMP%\CamfrogStatusChanger\logs\app.log` when the primary location is unwritable, including failures before logging is configured.
- Fail closed when Windows mutex creation fails, close duplicate-instance handles, and rely on Windows kernel handle cleanup after process termination instead of attempting unsafe stale-lock removal.
- Retry atomic config replacement up to four times on transient `PermissionError`; persistent failures leave the existing config intact and retain the completed temporary file for recovery. The config schema is unchanged.
- No multiprocessing or spawn usage was found, so no `freeze_support()` call was added. Local validation passed 250 pytest tests, `compileall`, `scripts/validate_repo.py`, and `git diff --check`; Windows CI and live Camfrog behavior remain unverified.

### Fixed — P3 moderation parsing safety

- Read bad-word history as explicit visible UIA `ListItem`/`Text` rows. Embedded newlines or history controls without row boundaries now pause moderation; continuation text cannot become a second sender.
- Require Unicode letter/number/mark token boundaries for configured terms, mask allowlisted examples before scanning, and retain the existing configured obfuscation variants. This conservative Thai boundary rule avoids matching a term inside an adjoining Thai word.
- Key moderation cooldowns by configured room and sender, independent of the matched term. Reject non-string or whitespace-padded nicknames instead of trimming them into valid targets; also reject control/format characters, separators, leading slashes, and overlong names. Reject command-template line/control injection. The exact outgoing command remains visible in confirmation.
- Add a rolling 60-second limit of five Auto kick submissions. A sixth attempt trips a process-lifetime kill switch, logs a warning, and persists Auto kick as disabled; defaults remain disabled and the config schema is unchanged.
- Add false-positive, spoof-row, nickname, template, cooldown, kill-switch, and adversarial regex regressions. Local validation passed 259 pytest tests, `compileall`, `scripts/validate_repo.py`, and `git diff --check`; Windows CI and live Camfrog behavior remain unverified.

### Fixed — P4 send path, DPI, and rotation

- Before a foreground Enter, poll for Camfrog to own the foreground window and confirm the selected Edit still belongs to that process and still contains the exact verified status. Recheck immediately before Enter; otherwise stop with an error and send no key.
- Replace fixed pre-Enter settling sleeps in the Win32 path with a bounded exact-text poll. Each background commit now verifies the target Edit again immediately before one Enter dispatch.
- Configure or confirm per-monitor-v2 DPI awareness before importing the dashboard or creating Tk windows. Coordinate fallbacks stay disabled unless that context is confirmed; their target Edit and foreground process are also reverified before Enter.
- Serialize concurrent manual and rotation status requests instead of rejecting the second request. The minimum interval uses an injectable monotonic clock for deterministic tests.
- Pass timezone-aware local datetimes into daily and overnight schedule checks, and use monotonic deadlines for rotation waits. Existing wall-clock inclusivity and overnight rules remain unchanged. The added history-source and single-character settings are versioned with a config schema 3 migration; no runtime dependency changed.
- Skip UIA keyboard input and Enter when the selected status combo has no uniquely identified Edit child; the guarded background route may still attempt the update.
- Regression tests cover foreground loss, text changes, missing/ambiguous Edit controls, focus recovery and loss, coordinate fallback gating, fake DPI APIs, DST transitions, midnight wrap, and eight concurrent Apply requests. Local validation passed 275 pytest tests, `compileall`, `scripts/validate_repo.py`, and `git diff --check`. Windows CI and live Camfrog behavior remain unverified.

### Fixed — Pre-push audit follow-up

- Stop the Win32 coordinate compatibility path when it cannot identify an Edit. Coordinates alone no longer authorize a paste, click, or Enter on an unknown Camfrog child.
- Add explicit config migrations through schema 3 for the history rotation source and one-character marquee setting. Migrate schema 1 message rows before merging defaults so saved `editor_lines` are preserved; existing custom marquee intervals remain unchanged.
- Regression tests reproduced the unidentified-control commit and missing config-version migration before the fixes. Full local validation passed 298 pytest tests, `compileall`, `scripts/validate_repo.py`, `pip-audit`, and `git diff --check`; exact-head GitHub checks remain pending.

### Fixed — P4 reviewer follow-up

- Load `win32con` in the native combo notification path so its `WM_COMMAND` notifications do not fail with `NameError`.
- Restore the prior clipboard in a `finally` block when coordinate status entry aborts before Enter.
- Let rotation pass a cancellation signal through the dashboard to `CamfrogController`; a stopped rotation now abandons a status still waiting for the apply lock before starting or sending it. Legacy one-argument callbacks remain supported.
- Keep cancellation results' `previous_value` empty until a previous Camfrog status has actually been read, while retaining the requested text in `new_value`.
- Add four regressions that failed against the prior code. Full local validation passed 302 pytest tests, `compileall`, `scripts/validate_repo.py`, and `pip-audit`; exact-head GitHub and Windows build checks remain pending. No live Camfrog action was performed.

### Fixed — P5 registry history dump

- Create the registry dump directory when needed and return a clear nonzero result for storage/scan errors or when no registry keys were scanned.
- Keep `winreg` access inside the Windows reader path and skip sensitive registry branches as well as sensitive value names.
- Add opt-in `--redact` masking for email addresses, phone-like numbers, and URLs. Redaction remains off by default, and dumps are documented as personal data that must not be shared.
- Require complete delimiters when carving binary history so truncated ASCII/UTF-16LE tails are ignored. Add fake-Registry and fixture coverage for sensitive-key exclusion, metadata prefixes, odd alignment, and truncated blobs.
- Preserve the config schema and read-only registry behavior. Local validation passed 286 pytest tests, `compileall`, `scripts/validate_repo.py`, and `git diff --check`; Windows registry access remains unverified.

### Changed — P6 repository hygiene and history review

- Replaced the release-note-heavy README with current install/run links, feature scope, security boundaries, and current verification limits. Moved historical release notes here in chronological order.
- Scanned 47 commits reachable from the checkout's available refs, 369 unique Git blobs, all 15 ZIP blobs, and 639 nested ZIP members, including binary `.pyc` files. All ZIP blobs were readable. The path-only report is `docs/operations/history-pii-scan-report.md`; no raw matched values are recorded. `gitleaks` and `trufflehog` were unavailable, so an offline identity/contact and high-confidence credential-pattern fallback was used; no private-key or common provider-token candidates were found.
- Prepared `docs/operations/history-pii-rewrite-runbook.md`. Git history was not rewritten, and no branch was force-pushed.
- Kept `CLAUDE.md`, `OPENCODE.md`, and `ecc-install.json`: CODEOWNERS, the repository validator, and AI integration documentation still reference them.
- Open PRs #3 and #4 have passing required checks and no merge conflict, but both still require review. Neither was merged.
- Added a pending EULA/legal review notice to the reverse-engineering documentation. Local validation passed 286 pytest tests, `compileall`, `scripts/validate_repo.py`, CommonMark parsing, and `git diff --check`. Tests ran in a temporary `/tmp` virtual environment with the pinned app dependencies; no Windows or live Camfrog checks were run.

### Changed — P7 build and dependency integrity

- Consolidated local batch entrypoints and the Windows workflow on `scripts/build_windows.py` for hash-locked setup, dependency audit, tests, compile checks, staged PyInstaller packaging, and manifest generation. The Python manifest writer is also used by the PowerShell compatibility wrapper.
- Added universal SHA-256-hashed runtime and build locks generated from `requirements.in` and `requirements-build.in`. Ubuntu CI installs with `--require-hashes`, audits the build lock, and uploads a JUnit test report; the Windows workflow uses the same builder and uploads the EXE with its SHA-256 manifest.
- Added fake-runner regression coverage for paths containing spaces and Thai text, manifest verification, audit invocation, rollback when manifest publication fails, and preservation of unrelated files under `build/`. Initial local P7 checks passed 295 pytest tests, hashed dependency installation, `pip-audit` with no known vulnerabilities, `compileall`, repository validation, workflow YAML parsing, and `git diff --check`.
- A manual Windows 11 x64 validation build of the pre-push-follow-up worktree passed 295 tests, `pip-audit`, `compileall`, and repository validation. PyInstaller produced a 17,308,673-byte validation executable with SHA-256 `ee006569d8d36fcdcc650823246e390f9f7a8503009eca12b50100d37e14fcc0`; the manifest matched and PE machine type was x64 (`0x8664`). This used Python 3.11.9 and does not include the two audit follow-up fixes; the checked-in Windows workflow pins 3.12, so exact-head GitHub Actions evidence remains pending. The executable was not launched, signed, or released.

### Changed — Camfrog status send and rotation

- Send status text by Unicode clipboard paste, verify the single target Edit, restore the prior clipboard, and dispatch one foreground Enter. A failed verification skips commit.
- Add a rotation source for read-only Camfrog Status History. History mode shuffles the observed rows, sends one row at a time, and waits the configured interval; Camfrog server acceptance remains unconfirmed.
- Add one-character marquee frames for the active Message 1–4 row, with 5, 10, 15, 20, and 25 second delays repeating. The existing minimum five-second send guard remains enforced.
- Route all status Apply controls, including the four message rows and standard-status action, through the same verified controller path. Stage-only remains no-commit.

### Fixed — PR review follow-up

- Route Windows copy/cut/paste in every Entry/Text editor through `CF_UNICODETEXT`; cancel paste when Unicode text is unavailable instead of accepting a lossy ANSI representation.
- Require the Windows application test and CodeQL checks in the repository administration helper, matching the checks observed on pull requests. Add the verified `policedbc` collaborator as a second code owner so independent approval is possible when `cvsz` authors a change.
- Reject generic UIA ComboBoxes as Camfrog status targets unless an exact automation ID or observed status value identifies them. Refuse background and coordinate fallbacks when UIA exposes an unverified generic target.
- Keep the dashboard visible when the tray fails to start, restore it if the tray thread later stops, and exit on close rather than leaving an unreachable hidden process.
- Allow the first auto-reply, moderation alert, or room-event alert immediately after startup; begin cooldown checks only after a prior action has a timestamp.
- Isolate Windows platform test doubles to each Camfrog module instead of mutating shared `os.name`, preserving Python 3.12/POSIX test behavior.
- Remove project-template bootstrap and inventory files so this checkout consistently documents the Camfrog application at its root.
- Default Make targets to `python3` on POSIX and `py -3` on Windows; document that executable builds are temporary workflow artifacts, not checked-in files.

### Repository layout

- Promoted the Camfrog Status Changer application, tests, documentation, Windows build assets, and preserved local build artifacts from the former app subdirectory to the repository root.
- Consolidated its Windows test/build workflow at the root and retained the repository baseline workflow.
- Isolated PyInstaller work output under `build/CamfrogStatusChanger-work` so build scripts no longer remove the adjacent Camfrog analysis files in `build/`.
- Kept the complete test suite in the Ubuntu baseline workflow after the root migration; it now installs the app requirements and runs pytest rather than selecting only the bootstrap test.

### Fixed — runtime follow-up

- Wired the existing **Allow foreground fallback** UI option into the controller instead of failing immediately after background verification fails.
- Added explicit foreground fallback flow: restore/focus Camfrog, use configured relative status target, replace one message, press Enter, and restore minimized state.
- Added status-change stages to error reporting so dialogs identify whether failure occurred at validation, rate limit, background verification, foreground fallback, or runtime exception.
- Normalized Camfrog executable paths to Windows backslash form for Detect, Browse, load, and save.
- Initialized COM in STA mode before loading the UI/controller stack to avoid pywinauto/comtypes apartment-mode churn.
- Reduced Windows PyInstaller warning noise by excluding unused Linux/macOS tray/UI backends while keeping Win32 tray support explicit.

### Fixed — audit follow-up

- Restrict Camfrog discovery to known client executable names or the exact configured executable path, so the status manager itself is not mistaken for an online Camfrog client.
- Stop status/room automation when multiple Camfrog windows or status controls match instead of sending to the highest-scoring guess; the Win32 fallback now preserves the ambiguity result and does not continue to coordinate fallback.
- Remove account-specific status text, owner metadata, email addresses, and secret-like values from fresh defaults and test fixtures.
- Upgrade Pillow to the minimum fixed version reported by the dependency vulnerability audit.
- Pin PyInstaller to the version used for the verified Windows candidate builds.
- Route the standard build entrypoint through the tested Windows builder and keep the current app process and published EXE until staged tests and packaging succeed.
- Fix Inspect error callbacks that referenced the exception variable after its `except` scope ended.
- Add `scripts/__init__.py` so repository tests reliably import the local bootstrap module when an unrelated installed `scripts` package exists.
- Exclude legacy release ZIPs containing account-specific identity/contact data from the new root `tags/` directory; only the neutral reverse-engineering kits were carried forward.

### Integrated — 2026-10-01

- Imported the historical `2.3.1-rc2` source bundle and documentation. This archive label is not the current application version; `version.py` is authoritative.
- Added background-first controller, Win32/UIA integration, known-client fingerprint profile and fail-closed fallbacks.
- Added four independent message slots and enforced `1 tick = 1 message = 1 set_status()`.
- Added sequential/random rotation and seconds/minutes/hours interval selection.
- Added TH/EN UI behavior, readable alerts, tray/startup design and hidden-console build flow.
- Fixed duplicate Ctrl+V behavior caused by stacked Tk paste bindings.
- Added read-only registry/history discovery, binary string carving, garbage filtering and explicit import-to-presets flow.
- Blocked generic `CButtonTS` commit guessing after it activated unrelated Camfrog controls/browser actions during testing.
- Implemented marquee as text-frame updates rather than unsupported markup.
- Replaced unsupported custom-status color markup with visible Unicode color markers.
- Added config recovery, single-instance behavior, log rotation and release SHA-256 manifest design.
- Added RE findings for `CSPacket020401.text_status` and Text Over Video `TOV_*` settings.

### Evidence baseline

The prior integrated implementation package reported 41 passing tests. Repository CI must independently validate each committed revision.

### Still unverified

- server-visible custom-status publication on the supported Camfrog build
- minimized/background-only end-to-end publication across client updates
- code-signing/Defender/SmartScreen behavior of the final Windows artifact

## Historical releases (chronological)

These notes describe earlier source snapshots and are not proof that a matching binary remains available or verified.

### 2.0.0-rc1 — Initial Windows companion

- Introduced manual custom-status application, sequential/random rotation, configurable intervals, tray/startup behavior, PID-based client discovery, native `CComboBoxTS` targeting with UI Automation compatibility, and a no-commit staging action.
- Added read-only Registry status discovery and sanitization, config recovery and atomic saves, a single-instance guard, concurrency/rate controls, rotating logs, and native-control diagnostics.
- Added optional visible-UI automation for private/room auto-reply and configured room-event phrases, plus public profile links, a Windows executable build, and a SHA-256 manifest.

### 2.0.0-rc2 — Native combo commit

- Fixed UIA ComboBox/Edit dispatch and native `CComboBoxTS` owner-chain commit notifications.

### 2.1.0-rc1 — Native profile diagnostics

- Added a version-gated static-analysis profile for the reviewed Camfrog x64 binary, class targeting for `CComboBoxTS`, `CEdit4ComboInnerTS`, and `CButtonStatusTS`, and safe diagnostics for status-related RVAs.
- Internal RVAs remained diagnostic-only and were not invoked.

### 2.1.1-rc2 — Background commit safety

- Stopped background clicks on generic `CButtonTS` controls and kept `CButtonStatusTS` diagnostic-only.
- Added edit-change notifications before combo commit. Registry import was limited to explicit status/custom sources, and the unreliable background-only commit mode was removed.

### 2.1.3-rc4 — Registry history reader

- Added a separate read-only History panel and an explicit import-to-presets action.
- Added aligned UTF-16LE and printable ASCII extraction from `REG_BINARY` values with metadata prefixes; generic profile metadata remained excluded.
- Added a history dump command. Its output can contain personal status text and registry paths and should not be shared; optional redaction is not a guarantee of anonymization.

### 2.1.4-rc5 — Four-field editor (superseded)

- The earlier editor combined four fields into one multiline status. Later versions use Message 1–4 as independent values, each applied separately.

### 2.2.0-rc2 — Merged RC2 additions

- Added the application icon to the app window, executable, and tray; embedded the icon as a runtime resource in both Windows build scripts.
- Added optional Random Color, Custom Color, Marquee, and EN/TH UI selection.
- Rotation applied one preset per interval. Color markup had no confirmed packet field and could display literally; marquee was repeated status submission rather than native animation.

### 2.2.3-rc5 — Message-per-tick and bilingual UI

- Added four independent status messages with per-row Apply actions and a searchable, categorized 50-entry Thai/English standard-status dropdown with favorites and persisted selection.
- Added JSON v1 and one-status-per-line TXT preset import/export with merge and deduplication; sequential and random rotation applied one non-empty row per tick.
- Added a five-second minimum send interval, local daily scheduling and overnight quiet hours, and one-write/one-Enter status submission. UI submission did not prove server publication.
- Expanded TH/EN localization, Unicode clipboard operations, and optional one-message-per-character marquee frames.

### 2.2.5-rc1 — Foreground status commit and chat automation

- Wrote the status once, verified the target Edit, then sent one foreground Enter. Server acceptance remained unconfirmed.
- Added the bilingual standard-status catalog, preset import/export, rotation scheduling, tabbed feature UI, optional disabled-by-default auto-reply, and repeated marquee status updates.
- Only two Text Over Video registry values had been found in the checked profile; other settings were not exposed for writing.

### 2.2.5-rc2 — Room commands and bad-word review

- Added per-action room command templates and exact-command confirmation. Templates stayed blank until verified for the target Camfrog build.
- Added optional visible-history bad-word review. Monitoring, room commands, and automatic kick remained disabled by default; UI submission could not verify permissions or server acceptance.

### 2.2.5-rc3 — Single-commit status and optional Auto kick

- Prevented retry typing after Camfrog consumed a committed status field.
- Added an explicit Auto kick setting, off by default, with the existing room, visible-control, draft, and cooldown checks.

### 2.2.5-rc4 — Room-event phrase notifications

- Added optional phrase matching against new visible room-history lines. The in-memory activity view kept only the room title and matched phrase; it did not infer semantic membership or role events.

### 2.2.5-rc5 — Thai/English moderation catalog

- Added categorized profanity, bypass, discrimination, and spam-related starter terms. Monitoring and Auto kick remained disabled; users had to review the broad catalog before enabling it.

### 2.2.5-rc6 — Feature tabs and multiline reply

- Grouped Setup, Status, History, Rotation, Auto reply, room commands, bad words, room events, and video overlay into separate tabs.
- Preserved multiline auto-reply text and made marquee repeatedly advance the active status text. Text Over Video editing stayed disabled until selectors and saved value formats could be verified.

### 2.2.5-rc7 — Read-only Text Over Video discovery

- Added process-scoped inspection of visible Camfrog Settings controls. The diagnostic saved sanitized UIA metadata and omitted Edit/ComboBox values; editing stayed disabled.

### 2.2.5-rc8 — Resilient Text Over Video inspection

- Scanned visible windows owned by the configured Camfrog process even when their titles differed from the main client window.
- Saved sanitized window metadata when UIA did not expose Text Over Video labels. Ambiguous client windows remained a stop condition.

### 2.2.5-rc9 — Public profile shortcuts

- Added a Web tab to open or copy a URL-encoded public Camfrog profile link and open the official profiles/leaderboard page. The app did not collect credentials, cookies, scrape the site, or edit profiles.

### 2.2.5-rc10 — Exact room targeting

- Required an exact configured room-title match for commands, moderation, and room-event notifications.
- Stored owner metadata and per-action target nicknames separately; owner metadata did not establish role or permission.

### 2.2.5-rc11 — Root migration audit candidate

- Restricted Camfrog process detection and stopped status/room automation when more than one client window or target control matched.
- Removed account-specific defaults, upgraded Pillow, restored the complete Ubuntu test suite, and retained the Windows test/build workflow.
- The historical RC11 Windows build was not launched against Camfrog. UI Automation, server publication, room actions, signing, and antivirus behavior remained unverified.
