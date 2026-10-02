# Camfrog Status Changer — Production Readiness

Version: 2.2.5-rc11

> RC10 and RC11 refer to prior candidate builds. Re-run the Windows workflow on the exact release candidate before using its build evidence; live Camfrog behavior remains unverified.

## Current audit evidence (2026-10-02)

- Latest post-follow-up local checks: 298 pytest tests passed; hash-locked dependencies installed, `pip-audit` reported no known vulnerabilities, and `compileall`, `scripts/validate_repo.py`, and `git diff --check` passed. The manual Windows 11 Enterprise x64 validation build below predates the two pre-push audit fixes and does not verify the current source. It produced a 17,308,673-byte validation EXE with SHA-256 `ee006569d8d36fcdcc650823246e390f9f7a8503009eca12b50100d37e14fcc0`; the manifest matched and PE machine type was x64 (`0x8664`). That host had Python 3.11.9 while the checked-in Windows workflow pins 3.12; exact-head GitHub Actions evidence remains pending. The validation EXE was not launched, signed, or released.
- P4 verifies the foreground PID and exact status Edit immediately before Enter; when UIA cannot uniquely identify an Edit, its foreground route sends no keyboard input. Coordinate fallbacks require confirmed per-monitor-v2 DPI awareness and a uniquely identified Edit; concurrent status sends serialize behind the monotonic minimum interval, and rotation windows use aware local time. The history-source and one-character marquee settings use config schema 3 migrations from schema 1 and 2; no runtime dependency changed.
- Pre-push audit follow-up blocks background coordinate clicks, pastes, and Enter when no Edit is identifiable. Full local validation passes; exact-head CI remains pending.
- P5 creates the dump directory, fails with nonzero status on scan/storage/write errors or zero scanned keys, filters sensitive key branches, and provides opt-in email/phone-like/URL redaction. Default dumps still contain personal status text and source metadata; never share them. No config schema or dependency changed.
- An earlier `make ci` snapshot on 2026-10-02 passed 150 tests on Python 3.14.4; the later 298-test post-follow-up run supersedes that count. The Windows build and live Camfrog behavior still require exact-head Windows/runtime evidence.
- Python compile checks, repository structure/local Markdown link validation, YAML parsing for 13 workflow/config files, and isolated Ruff correctness/syntax checks passed.
- A prior Bandit run reported no medium/high-severity findings. The current P7 `pip-audit` run reported no known vulnerabilities in the hash-locked build dependencies.
- A prior RC11 Windows workflow run passed 146 tests and 3 subtests and built a Windows x64 executable with PyInstaller 6.22.3. Its executable and manifest are workflow artifacts, not files in the Git checkout; re-run the workflow on the exact release candidate before release.
- The executable was not launched against Camfrog. UIA controls, live status submission, room commands, server-visible behavior, code signing, and antivirus behavior remain unverified.
- Previously built RC10/RC11 executables are historical candidates and do not establish evidence for a later source commit.

## P7 Windows validation build (2026-10-02; not a release artifact)

- [x] A sanitized worktree bundle based on HEAD `1a9c27455ea88fe3c3f4d0d69d21963a3604f14f` was copied to Windows 11 Enterprise x64; the local and host archive hashes matched (`9e11db66815d1212c0248ab53197336975939b05b84529a91079fed12ddb2e7b`). The bundle omitted `.git`, generated build outputs, and archived binaries.
- [x] The Windows builder ran with Python 3.11.9. All 295 pytest tests passed, `pip-audit` found no known vulnerabilities, and compile checks plus `scripts/validate_repo.py` passed.
- [x] The validation EXE is 17,308,673 bytes, has SHA-256 `ee006569d8d36fcdcc650823246e390f9f7a8503009eca12b50100d37e14fcc0`, and is PE x64 (`0x8664`). The generated release manifest contains the same SHA-256.
- [ ] Exact-head GitHub Actions evidence remains pending; the repository workflow pins Python 3.12 and this host has Python 3.11.9. The build bundle had no Git metadata, so the result is not an exact committed-revision build.
- [ ] The validation EXE was not launched, signed, or released. Camfrog UI, live status acceptance, and room behavior remain unverified.

## Evidence from the earlier RC10 candidate

- Source compiles successfully on the build environment.
- The RC10 regression suite passed 123 tests on the Windows build host, with Windows and focused Linux compile checks passing at that time.
- Configuration writes are atomic (`config.tmp` + `os.replace`).
- Corrupt configuration is backed up and automatically recovered to safe defaults.
- Single-instance Windows mutex prevents duplicate tray/background workers.
- Manual and scheduled status changes share a non-blocking apply lock.
- Minimum apply interval rate-limits accidental rapid status changes.
- A verified UIA status write focuses Camfrog and sends one real Enter; the coordinate mouse/clipboard fallback remains opt-in.
- Native status fallbacks verify the text before Enter and do not retry/overwrite when Camfrog consumes or clears the field after Enter. UIA/field evidence remains separate from server acceptance.
- Auto rotation applies the first eligible row immediately and waits the configured delay between later rows; every row uses one status write followed by one Enter.
- Room action templates and bad-word monitoring are disabled by default. Manual commands require confirmation; a separate `auto_kick` setting can opt in to a configured bad-word kick. Both paths use visible UIA controls; role checks and server results remain unverified.
- Room commands, bad-word monitoring, and room-event notifications require an exact configured room title match, case-insensitive. Per-action targets and an owner nickname are persisted; the owner nickname does not verify current room privileges.
- Fresh configs seed 129 terms from the categorized Thai/English catalog; monitoring and `auto_kick` remain disabled. Existing term lists are preserved. The filter supports selected obfuscation patterns and safe-word exceptions; operators should review terms before enabling moderation.
- Optional room-event notifications match configured phrases in new visible room-history lines. They are disabled by default and retain only room title plus matched phrase in an in-memory activity view; semantic event detection and current-build selectors remain unverified.
- Registry import is read-only and filters numeric, account-like, opaque/binary and sensitive-key data.
- Logs rotate at 2 MiB with five backups rather than growing without bound.
- Windows startup uses HKCU Run and `pythonw.exe` in source mode to avoid a console window.
- Build gate runs tests and compile checks before creating the EXE.
- Release build generates SHA-256/size metadata in `release-manifest.json`.
- Runtime dependencies are pinned in `requirements.txt`.
- The Web tab opens an official public profile or directory URL and copies the profile URL. It stores only the nickname; sign-in and profile edits stay on Camfrog's website.

## RC9 candidate build verification (2026-10-02)

- [x] Windows x64 one-file EXE built in a unique temporary directory with Python 3.11.9 and PyInstaller; the checkout's existing `build`/`dist` folders and Camfrog processes were not touched.
- [x] Windows regression suite passed 116 tests and `compileall` passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc9.exe` is 17,260,687 bytes with SHA-256 `8e80a94ef8eb327443d993e4d5cf43ad0c8f44b7e5a3fb79c138c5dd405fe470`; the local copy, Windows host copy, and release manifest match.
- [x] PE inspection confirms x64/PE32+ Windows GUI with icon resource types 3 and 14. PyInstaller archive inspection confirms `app.ico` and `bad_word_starters.json` are bundled and `PIL._avif` is excluded.
- [ ] Browser navigation is delegated to the user's default browser; profile login/editing and website behavior have not been tested by this app.
- [ ] Packaged dashboard startup and live Camfrog status/room behavior remain unverified; no room action was sent.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.

## Windows user config update (2026-10-02)

- [x] The existing `%APPDATA%\CamfrogStatusChanger\config.json` was backed up before both updates; only the requested room profile and room title filter were changed in the later update.
- [x] The owner nickname, friend target, exact room title, own nickname, and profile nickname are saved locally. Room-action and moderation enablement, configured templates, terms, and cooldowns were preserved.
- [x] Strict UTF-8 decoding and JSON parsing passed with no BOM; all 129 saved moderation terms remain present, including 67 Thai terms.
- [x] Read-only UIA inspection found the room history and composer host share Automation ID `1002`; the history resolver can disambiguate the history by visible message-line shape. The adjacent candidate Send control is ID `1307`, but it is owner-drawn, disabled while the composer is empty, and does not expose UIA `InvokePattern` in that state. Input and Send selectors remain unset because the composer ID is duplicated and the Send action is not verifiable through the current UIA provider.
- [ ] Room monitoring and command submission remain unverified in the running Camfrog client. No room command, message, or moderation action was sent.
- [x] No Camfrog room command, message, or moderation action was sent during either config update.

## RC10 candidate build verification

- [x] Windows x64 one-file EXE built in a unique temporary directory with Python 3.11.9 and PyInstaller 6.22.3; existing checkout build/dist files and Camfrog processes were not touched.
- [x] Windows regression suite passed 123 tests and Windows `compileall` passed. Local focused Linux regression tests passed 32 tests; local compile checks passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc10.exe` is 17,263,003 bytes with SHA-256 `08fd55d4c6850020f98e1898747faae339f0f3d8abd8c9ad9d67d1a6fefab8e8`; the downloaded file matches the Windows build host.
- [x] PE inspection confirms x64/PE32+ Windows GUI and icon resource types 3 and 14. PyInstaller archive inspection confirms `app.ico` and `bad_word_starters.json` are bundled and `PIL\\_avif` is excluded.
- [ ] The executable is unsigned and has not been scanned with Windows Defender or organizational malware scanning.
- [ ] Packaged dashboard startup and live Camfrog status/room behavior remain unverified; no room action was sent.

## RC6 candidate build verification (2026-10-02)

- [x] Windows x64 EXE built in an isolated build directory with Python 3.11.9 and PyInstaller 6.22.3.
- [x] Windows regression suite passed 102 tests; Windows `compileall` passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc6.exe` is 16,334,744 bytes with SHA-256 `288282a90ba24ba8c9e482588e2dc444391f675038b2d805884f8491a3375f82`; downloaded local copy and Windows build-host copy match.
- [x] PE inspection confirms x64/PE32+ and icon resource types 3 and 14. PyInstaller archive inspection confirms `app.ico` and `bad_word_starters.json` are bundled and `PIL\\_avif` is excluded.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.
- [ ] Packaged dashboard startup and live Camfrog status/room behavior were not tested. The supplied recording maps the visible Text Over Video page and preview, but stable UIA selectors and stored value formats remain unverified.

## RC8 candidate build verification

- [x] Windows x64 EXE built in an isolated temporary source/build directory with Python 3.11.9 and PyInstaller 6.22.3; the existing checkout `build`/`dist` and Camfrog processes were not touched.
- [x] Windows regression suite passed 106 tests; Windows compile check passed. The focused Text Over Video inspector suite passed 4 tests on Linux, and Linux compile checks passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc8.exe` is 17,256,730 bytes with SHA-256 `eec7391d20d47d475c8db17b93c81afb2368afaf6e36b9b5f9efe6633d9e4548`; the local copy matches the Windows build host and generated manifest.
- [x] PE inspection confirms x64/PE32+ and icon resource types 3 and 14.
- [ ] Interactive Camfrog Text Over Video inspection has not yet been rerun with RC8; packaged dashboard startup and live status/room behavior remain unverified.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.

## RC7 candidate build verification

- [x] Windows x64 EXE built in a unique temporary directory with Python 3.11.9 and PyInstaller 6.22.3; the build did not stop or modify existing CamfrogStatusChanger processes or clean the checkout's `build`/`dist` folders.
- [x] Regression suite passed 104 tests on Linux and 104 tests on the Windows build host; compile checks passed on both.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc7.exe` is 16,337,289 bytes with SHA-256 `1878a76d914447f565e8d837859cb0994b0f7991dbdc1f86484b5817325c4e72`; the Windows host and local copies match.
- [x] PE inspection confirms x64/PE32+ and icon resource types 3 and 14. PyInstaller archive inspection confirms `app.ico` and `bad_word_starters.json` are bundled and `PIL\\_avif` is excluded.
- [ ] The new Text Over Video inspector has not yet run against Camfrog in the interactive Windows session; packaged dashboard startup and all live status/room behavior remain unverified.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.

## RC5 candidate build verification (2026-10-02)

- [x] Windows x64 EXE built with Python 3.11.9 and PyInstaller 6.22.3; Windows source suite passed 97 tests and `compileall` passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc5.exe` is 17,245,706 bytes with SHA-256 `d20cdc687ae98accca2d0494b5281850f50c2fcc19efbd1dac576d817e056057`. The local copy and Windows build-host copy hashes match.
- [x] PE inspection reports x64/PE32+ and icon resource types 3 and 14. PyInstaller archive inspection confirms `bad_word_starters.json` is bundled and `PIL\_avif` is excluded.
- [x] The build log reports `Build complete!`; the SSH wrapper returned exit code 1 after output redirection. The artifact was independently checked by hash, size, PE metadata, and archive listing.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.
- [ ] Packaged UI startup and live Camfrog status/room behavior were not tested.

## Previous RC2 candidate build verification (2026-10-02)

- [x] Windows x64 EXE built with Python 3.11.9 and PyInstaller 6.22.3.
- [x] Source regression suite passed on the Windows build host (82 tests); compile check passed.
- [x] The host and downloaded EXE SHA-256 values match; PE inspection confirms x64 and embedded icon resources. See `dist/release-manifest-2.2.5-rc2.json`.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.
- [ ] The packaged EXE was not launched because existing Camfrog/manager processes were active; live status and room behavior remain unverified.

## RC4 candidate build verification (2026-10-02)

- [x] Windows x64 EXE built with Python 3.11.9 and PyInstaller 6.22.3; Windows source suite passed (90 tests), and compile check passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc4.exe` is 16,321,008 bytes with SHA-256 `4d7edcd11ae708f886cbbe80d7bf5729e368ca701174923dca2d16b1b33e3e2f`; the Windows build stage, local copy, and `E:\CamfrogStatusChanger-2.2.5-rc4.exe` hashes match.
- [x] PE inspection confirms x64 (`0x8664` / PE32+) and icon resource types 3 and 14. An isolated packaged launch created a separate default config; Camfrog auto-start, rotation, auto-kick, and room-event monitoring were all disabled in that config. No Camfrog status or room action was exercised.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.
- [ ] Interactive UI, live Camfrog status acceptance, and room-event/room-action behavior remain unverified.

## RC3 candidate build verification (2026-10-02)

- [x] Windows x64 EXE built with Python 3.11.9 and PyInstaller 6.22.3; Windows source suite passed (87 tests), and compile check passed.
- [x] `dist/CamfrogStatusChanger-2.2.5-rc3.exe` is 16,312,531 bytes with SHA-256 `e8df54b5540beb5238a3c615cc7cef139699755e30d37771f140cccc180a71b0`; the host and copied artifact hashes match.
- [x] PE inspection confirms x64 and embedded icon resources. An isolated packaged-startup smoke test created its own config with rotation and Camfrog auto-start enabled and auto-kick disabled, then exited cleanly.
- [ ] The candidate is unsigned and has not been scanned with Windows Defender/organizational malware scanning.
- [ ] Interactive UI, live Camfrog status acceptance, and room-action behavior remain unverified.

### Package-size comparison

- The 2.2.5-rc7 artifact is 16,337,289 bytes, 2,545 bytes larger than RC6. The difference is small and does not by itself identify which source/build inputs account for the change.
- The 2.2.4-rc2 artifact is 21,511,052 bytes (about 20.5 MiB); 2.2.5-rc4 is 16,321,008 bytes, a reduction of 5,190,044 bytes (about 24.1%). RC4 is 8,477 bytes larger than RC3.
- PyInstaller archive inspection found a 4,321,271-byte compressed `PIL\_avif.cp311-win_amd64.pyd` entry in 2.2.4-rc2 that is absent from both 2.2.5-rc3 and 2.2.5-rc4. The app's Pillow usage loads its ICO tray icon; no AVIF load path was found. This is the largest measured contributor, while other archive contents also differ.
- The old release manifest does not record the exact Pillow wheel/build, so the archive diff proves what was bundled but not why that historical build collected AVIF. The size change does not by itself indicate removed app features.
- The 2.2.5-rc5 artifact is 17,245,706 bytes, 924,698 bytes larger than RC4. Its bundled JSON catalog is 3,737 bytes; archive inspection shows `_asyncio.pyd` and `_overlapped.pyd` among the additional entries, while `PIL\_avif` remains excluded. The catalog alone does not explain the total size difference.

## Remaining P0 release gates

Behavior checks require an interactive Camfrog client and a controlled test room. The scanner and policy checks are standalone release gates.

1. Verify `Apply now` changes the server-visible Camfrog custom status, not only local control text.
2. Verify the same status change while Camfrog is minimized and not focused.
3. Verify status survives/reconciles after Camfrog reconnect/login refresh.
4. Verify sequential and random rotation for at least 10 cycles at 5–10 second test intervals, then normal intervals.
5. Verify that a verified status write focuses Camfrog only for the Enter commit and does not move the physical mouse.
6. Verify Camfrog update/restart does not change `CComboBoxTS` targeting unexpectedly.
7. Test Windows startup, tray close/reopen, single-instance behavior, log rotation, and clean exit.
8. Scan the final EXE with Windows Defender and organizational malware scanning policy; do not bypass detections with exclusions.
9. Confirm Camfrog terms/policies permit the intended automation before broad distribution.
10. In a controlled room, verify manual confirmation, opt-in Auto kick, saved kick template, cooldown, and exact-room targeting using test accounts; confirm false-positive behavior before enabling it in a normal room.

### Earlier Windows live evidence for 2.2.4-rc2 (2026-10-01)

- A temporary status value remained exact in the Camfrog Edit after one foreground keyboard Enter, and the previous value was restored successfully.
- This does not confirm that another account or the Camfrog service observed the temporary value. That package was built but not launched because the existing manager and Camfrog processes were left running.

## Acceptance criteria

Production-ready may be claimed only after every P0 gate above has timestamped evidence. A passing unit-test suite alone is not production evidence.

## Recommended evidence bundle

Store under `evidence/<YYYYMMDD-HHMMSS>/`:

- `self-test.json`
- `camfrog-native-controls-safe.json`
- redacted `app.log`
- screenshots/video showing before/after status from another Camfrog account if possible
- `release-manifest.json`
- Windows Defender scan result
- exact Camfrog version and executable SHA-256

## Native reverse-engineering gate (2.1.0-rc1)

- [x] Exact known Camfrog binary SHA-256 profile recorded.
- [x] Known native UI classes used for targeting; status commit controls are diagnostic-only.
- [x] Status-related RE RVAs recorded as diagnostics only.
- [x] Unknown Camfrog binary versions fail back to generic UI/Win32 path; no internal function invocation.
- [ ] Dynamic trace proves the exact UI commit -> ChangeStatus -> SetSelfStatus -> protobuf serializer chain.
- [ ] ABI/object lifetime for any proposed internal call is proven before enabling a direct native adapter.
- [ ] Remote-account E2E confirms the server-visible custom status after a background change.


## Detect preferred executable

The Detect action first checks `%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe`, then falls back to exact client executable discovery and legacy Program Files locations. It does not treat the similarly named manager executable as Camfrog. Automation stops when multiple matching client windows are open instead of guessing an account.

### 2.2.3-rc5 acceptance additions
- [x] Four independent message slots; no multiline compose across slots.
- [x] One scheduler tick invokes one status apply only.
- [x] Legacy `editor_lines` migrates to Message 1/2 without joining the values.
- [x] TH/EN covers main UI and automation option values.
- [x] Random Color/Marquee style exactly one outgoing message per tick.
