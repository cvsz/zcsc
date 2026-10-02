# ZeaZDev-CamfrogStatusChanger

> Camfrog Status Changer 2.2.5-rc11 is the Windows desktop application in the ZeaZDev-CamfrogStatusChanger project. RC11 was built from the root-migrated source and its Windows test suite passed. The RC10 executable and its manifest are historical artifacts and do not contain the audit fixes. Camfrog UI and live service behavior have not been tested with RC11.

## 2.2.5-rc11 — Root migration audit fixes

- Camfrog process detection uses exact client executable names or the configured executable path, so the status manager is not mistaken for an online client.
- Status and room automation stop when multiple client windows or status controls match; the app does not guess an account or fall through to a coordinate write.
- Fresh status presets are blank and user-specific identities were removed from source defaults and test fixtures.
- Pillow is pinned to 12.3.0 after the dependency audit reported vulnerabilities in the earlier version.
- CI again runs the complete test suite on Ubuntu and retains the Windows test/build job.
- The Windows build passed on Python 3.11.9 with PyInstaller 6.22.3; its full suite passed 146 tests and 3 subtests, and `compileall` passed. The x64 artifact and matching manifest are in `dist/2.2.5-rc11-windows-x64/`.
- The executable has not been launched against Camfrog. UI Automation, status submission, room actions, signing, and antivirus behavior remain unverified.

## 2.2.5-rc10 — Exact room targeting

- Room commands, bad-word monitoring, and room-event notifications now require an exact configured room name match (case-insensitive), including Camfrog's observed `: Video Chat Room` window-title suffix.
- Room control settings save the room title, owner nickname, and a separate target nickname per action. Choosing an action restores its saved target.
- Source defaults remain generic and disabled. The owner nickname is profile metadata; the app does not infer Camfrog roles or server permissions.
- UI Automation control IDs are still required for room history, message input, and send controls. No live room action was tested by this change.

## 2.2.5-rc9 — Camfrog web profile shortcuts

- Added a Web tab to save one nickname, open its public Camfrog profile, copy the profile link, or open the official profiles and leaderboard page.
- Nicknames are encoded as a single HTTPS path segment. The app does not ask for Camfrog credentials, read browser cookies, scrape the website, or edit profile data; sign-in and profile changes stay on the official site.
- Room commands and bad-word monitoring remain separate opt-in features and are disabled until explicitly configured.

## 2.2.5-rc8 — Resilient Text Over Video inspection

- The read-only inspector scans visible windows owned by the configured Camfrog client process, including Settings windows with different titles.
- Status and room automation targets one unambiguous Camfrog client. If multiple client windows match, close the extra client windows and retry; the app does not guess which account to control.
- If UI Automation does not expose Text Over Video labels, the inspector saves sanitized Camfrog window metadata as a diagnostic. Window titles outside the safe Camfrog labels and Edit/ComboBox values are omitted.

## 2.2.5-rc7 — Read-only Text Over Video control discovery

- Added **Inspect visible Camfrog Settings controls** to the Video overlay tab. It is process-scoped, read-only, and writes only sanitized UIA metadata to `tov-uia.json`; Edit/ComboBox values are omitted.
- Updated the Text Over Video evidence from the 2026-10-02 recording. Editing remains disabled until actual UIA selectors and saved value formats are verified.

## 2.2.5-rc6 — Feature tabs, multiline reply, and continuous marquee

- Refactored the dashboard into one tab per feature: Setup, Status, History, Rotation, Auto reply, Room commands, Bad words, Room events, and Video overlay. Open a feature with one click; its controls stay grouped on that page.
- Auto reply accepts multiline text and preserves line breaks when saving and sending one reply.
- Marquee now repeatedly advances the selected status text at the configured frame interval. During rotation, it advances the current row until that row's rotation interval expires. Uncheck **Marquee** to stop a manual run.
- **Allow background Win32 fallback when UIA cannot verify** is in the **Rotation** tab. It only permits fallback after UIA cannot verify the field; a verified UIA send still brings Camfrog forward to send Enter.
- In RC6, Text Over Video editing remained disabled while its live selectors and saved value formats were unverified.

# Camfrog Status Changer 2.0.0-rc2

RC2 fixes UIA ComboBox/Edit dispatch and native CComboBoxTS owner-chain commit notifications.

## 2.2.5-rc5 — Categorized Thai/English moderation catalog

- Added `bad_word_starters.json` with direct profanity/anatomy, bypass/leet variants, hate/discrimination, and spam/gambling/substance categories, plus obfuscation regexes and a small safe-word allowlist.
- New configs receive the catalog terms; monitoring and Auto kick remain disabled. Existing custom terms remain intact, and **Add all categorized terms** appends only missing entries.
- The filter recognizes configured English words at token boundaries and selected punctuation/spacing variants. Review the broad catalog before enabling moderation or Auto kick.

## 2.2.5-rc4 — Room event phrase notifications

- Optional room-event notifications match configured phrases against newly appended visible room-history lines. The feature is off by default and needs the room title/history UIA selectors.
- The in-memory activity view keeps only the room title and matched phrase; it does not persist raw chat lines. This is phrase matching, not semantic detection of member/role events, and current Camfrog selectors/server behavior still need a controlled live-room check.

## 2.2.5-rc3 — Single-commit status flow and configurable bad-word kick

- Native status fallbacks now treat a verified text field followed by one Enter as the commit attempt. They do not retry by typing the payload again when Camfrog consumes/clears the field; the server result remains unverified.
- Bad-word moderation has an explicit **Auto kick** setting. It is off by default. When enabled with room actions and a kick template, a new configured match submits that command without a prompt, subject to the existing cooldown and visible UIA/room/draft checks. When off, each match still asks for confirmation.

## 2.2.5-rc2 — Confirmed room commands and bad-word review

- Room commands for `op`, `friend`, `admin`, `owner`, `mute`, `kick`, and `ban` use per-action slash-command templates. Templates are blank by default; configure only syntax verified for your Camfrog build.
- Every room command requires a confirmation showing the exact command. The app uses the configured visible room input and send controls, will not replace a non-empty draft, and cannot verify room permissions or server acceptance.
- Optional bad-word monitoring reads only new visible room-history lines, ignores the configured own nickname, and matches case-insensitive configured terms. By default, a match opens a confirmation showing the room, sender, term, message, and configured kick command. Automatic kick requires its separate opt-in setting.
- Room commands and bad-word monitoring are disabled by default. Configure the Room chat UIA selectors, command templates, terms, and cooldown in the app, then save. Test the command syntax with a non-disruptive action first.

## 2.2.5-rc1 — Foreground status commit and chat automation

- Status entry is written once and committed with one Enter to the verified Camfrog Edit. The sender does not retype the payload, press Enter on the parent combo, or click a second control.
- After UIA verifies the single text write, the sender focuses that editor and delivers one real keyboard Enter. This is required by Camfrog's custom status combo; a background `WM_KEYDOWN` is not treated as a reliable commit.
- The success result confirms the verified input and Enter dispatch; Camfrog/server acceptance is not independently confirmed by this UI integration.
- The standard catalog has 50 EN/TH pairs, search, categories, favorites, and persisted selection.
- Presets support JSON v1 and one-status-per-line TXT import/export. Imports merge and deduplicate.
- Rotation sends the first eligible row immediately, then one row after each configured delay. It supports a local-time daily window and overnight quiet hours; rows are skipped while outside the allowed window.
- TOV scanning found only `TOV_MigratedFromCF6=1` and `TOV_Transparent=128` in the checked profile. Other settings are not yet safe to expose or write.
- The dashboard separates Setup, Status, History, Rotation, Auto reply, Room commands, Bad words, Room events, and Video overlay into dedicated tabs.
- Auto respond can monitor configured private-chat and room-chat UIA controls and submit one editable reply. The reply editor preserves line breaks and sends the multiline text as one message. It is disabled by default and requires explicit selectors for each enabled chat type.
- The Marquee option repeatedly updates the selected Camfrog status to advance the visible text frame. Each frame is a separate status change; set its interval in the Status tab and uncheck Marquee to stop. Rotation animates the current row until its normal row interval expires.
- The Rotation tab contains **Allow background Win32 fallback when UIA cannot verify**. This only enables background fallback after the preferred UIA path cannot verify text. A verified UIA status commit still brings Camfrog forward to send one real Enter. The separate coordinate fallback also brings Camfrog forward.

# Camfrog Status Changer 2.0.0-rc1

Windows desktop utility for user-controlled Camfrog custom-status presets and rotation. A verified status apply briefly focuses Camfrog to send one real Enter; it does not move the physical mouse on that path.

## Features

- Manual custom-status apply
- Sequential/random rotation
- Seconds/minutes/hours interval selection
- System tray operation and Windows startup
- PID-based Camfrog window detection
- Native `CComboBoxTS` targeting plus UI Automation compatibility
- Separate **Stage only (no Enter)** action for foreground draft verification; the normal **Send to Camfrog** action keeps its existing commit flow
- Read-only Camfrog registry preset discovery with sanitization
- Config corruption recovery and atomic saves
- Single-instance guard
- Apply concurrency/rate-limit guardrails
- Rotating logs
- Safe native-control diagnostics
- Optional private-message and room-chat auto response using visible UI Automation controls
- Optional configured-phrase room-event notifications using visible UI Automation controls
- Public Camfrog profile and leaderboard shortcuts through the default browser
- Hidden-console Windows EXE build
- Release SHA-256 manifest

## Development test

```cmd
run_dev.bat
```

## Self-test

```cmd
py self_test.py
```

## Safe diagnostic

With Camfrog running:

```cmd
py diagnose_camfrog.py
```

Output is stored under `%APPDATA%\CamfrogStatusChanger`.

## Production-candidate build

```cmd
build_exe_fixed.bat
```

Artifacts:

```text
dist\CamfrogStatusChanger.exe
dist\release-manifest.json
```

The build fails if regression tests or compile checks fail.

## Runtime data

```text
%APPDATA%\CamfrogStatusChanger\config.json
%APPDATA%\CamfrogStatusChanger\logs\app.log
%APPDATA%\CamfrogStatusChanger\self-test.json
%APPDATA%\CamfrogStatusChanger\camfrog-native-controls-safe.json
%APPDATA%\CamfrogStatusChanger\auto-respond-uia.json
```

## Auto respond setup

Auto respond is disabled by default. Open the **Auto reply** tab, then open the private chat and room chat windows that should be monitored. Click **Inspect chat controls** and review `auto-respond-uia.json`. The report includes visible window titles and UIA control type, Automation ID, and class metadata; chat message text is omitted. Set the title fragment and exact history, message-input, and send-button Automation IDs for each enabled chat type, enter your exact Camfrog nickname, set a reply, and save. The multiline reply box preserves internal line breaks and invokes the configured Send button once for the complete reply.

The responder only considers newly appended visible lines in `sender: message` form. It ignores the configured nickname, establishes a baseline on startup, waits for an empty message-input field, and requires a UIA `InvokePattern` on the configured send button. It does not focus a window, replace an existing draft, or use Camfrog protocol/session internals. Cooldown is per sender and conversation. A UIA submission does not independently prove that Camfrog's server accepted the reply. Leave auto respond off until the selectors have been checked against your Camfrog build.

## Room command and bad-word setup

Room commands require an exact room name plus message-input and send-button UIA IDs. The configured name is matched case-insensitively against the visible room window, allowing only Camfrog's observed `: Video Chat Room` suffix. Save a target nickname separately for each action; choosing **friend** restores that action's saved target. The owner nickname is saved as profile metadata and does not establish room permissions. Enter a one-line command template for each action with exactly one `{username}` placeholder, for example `/kick {username}` only if that syntax is valid in your Camfrog room. Templates are not prefilled because command syntax and permissions can vary. Each manual action shows the exact outgoing command for approval.

Bad-word monitoring additionally needs the Room history UIA ID and your exact Camfrog nickname. It only inspects the configured exact room title. Fresh configs include a categorized Thai/English starter catalog in `bad_word_starters.json`: direct profanity/anatomy, bypass and leet variants, hate/discrimination terms, and spam/gambling/substance terms. Monitoring and **Auto kick** remain disabled. Existing custom terms are preserved; use **Add all categorized terms** to add missing entries, then save. Review the broad catalog before enabling moderation. Matching is case-insensitive, permits selected punctuation/spacing variants, and uses token boundaries for English terms. A small allowlist avoids matching configured terms inside examples such as `assassin`, `class`, `ฟักทอง`, `กล้วย`, `ควัน`, and `สกัด`. Only new visible `sender: message` lines are checked, and the monitor establishes a baseline when it starts. With **Auto kick** off, each match asks whether to send the configured kick command. Turning it on allows the saved rule to send that command without a prompt. When manual confirmation is needed, matched chat text appears transiently in the prompt and is not persisted to an audit log. The owner nickname is not proof of current Camfrog permissions; server authorization and the moderation result are not verified.

## Security model

- Does not store Camfrog passwords.
- Registry status discovery is read-only.
- Sensitive registry key/value names are excluded from status parsing.
- Verified status submission uses a foreground keyboard Enter because Camfrog's custom combo does not reliably commit from a background key message.
- Do not add antivirus exclusions simply to suppress an alert; investigate/sign/scan the final artifact instead.

See `PRODUCTION-READINESS.md` for release gates that still require a real Windows + Camfrog E2E run.

## 2.1.0-rc1 native profile update

This build includes a version-gated static-analysis profile for the exact Camfrog x64 binary supplied during testing (SHA-256 `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`). The profile improves native class targeting for `CComboBoxTS`, `CEdit4ComboInnerTS`, and `CButtonStatusTS` and adds safe diagnostics for the discovered status-related RVAs.

The application **does not call the discovered internal RVAs directly**. Those addresses remain diagnostic-only until their runtime ABI/call chain is verified, avoiding crashes and state corruption when Camfrog changes. Run `py diagnose_camfrog.py` to create `%APPDATA%\\CamfrogStatusChanger\\camfrog-native-diagnostic-safe.json` with the binary fingerprint, profile match, class matches, and sanitized control inventory.

## 2.1.1-rc2 safety fix

- Generic Camfrog `CButtonTS` controls are never clicked by background automation.
- `CButtonStatusTS` remains diagnostic-only; current status submission does not click a control.
- Added edit-change notifications (`EN_UPDATE`, `EN_CHANGE`) before combo commit.
- Registry preset import now treats only `status`/`custom` paths or value names as status sources; generic `ProfileInfo` values such as nicknames are excluded.
- The old `Background only` control was removed because Camfrog's custom status combo requires a real foreground Enter after verified text entry.
- Runtime status operations contain no browser/URL launch path.


## 2.1.3-rc4 real history reader

- `Read Camfrog History` now fills a separate read-only History panel instead of silently contaminating Presets.
- `Import all → Presets` is explicit and user-controlled.
- REG_BINARY history values are carved as aligned UTF-16LE and printable ASCII, including blobs with metadata prefixes.
- Only explicit `status` / `custom` registry sources are parsed; nicknames/profile metadata remain excluded.
- Run `py registry_history_dump.py` to write `%APPDATA%\CamfrogStatusChanger\camfrog-history-sources-safe.json` containing decoded status text and the exact registry source path/value name.

## 2.1.4-rc5 — Earlier four-line editor behavior (superseded)

This historical release exposed four fields that were composed into one multiline status:

- Line 1 / text1
- Line 2 / text2
- Line 3 / text3
- Line 4 / text4

The current editor treats Message 1..4 as separate status values. Each row applies independently. Rotation sends the first eligible non-empty row immediately, then sends one row after each configured delay. Values persist in `status.editor_messages`.


## Merged RC2 additions

- `app.ico` is derived from `dist/zttato.png` and used for the app window, executable, and system tray.
- Both Windows build scripts embed `app.ico` as a runtime resource; the standard build preserves unrelated files in `dist`.
- Style controls: **Random Color**, **Custom Color**, and **Marquee** as opt-in controls.
- UI language selector: **EN / TH**.
- Rotation remains **1 preset per interval**.
- The RC2 baseline used a two-line payload; the current release uses the independent Message 1..4 behavior below.
- History reader, native profile, safe-commit guardrails, hidden-console build and production build gates remain included.

> Random Color and Custom Color wrap the outgoing status string in the configured text-format template. The target packet has no confirmed color field, so Camfrog may display the markup literally; rendering must be verified against the target build. Marquee sends one generated text frame per rotation tick and is not a native animation.


## Detect preferred executable

The Detect action first checks `%LOCALAPPDATA%\Programs\Camfrog Video Chat\Camfrog Video Chat.exe`, then falls back to exact client executable discovery and legacy Program Files locations. It does not treat the similarly named `CamfrogStatusChanger.exe` manager as the Camfrog client. If running clients have different executable paths, select the intended client with Browse; if multiple windows belong to the selected client, close all but the intended client before automation.

## 2.2.3-rc5 — Message-per-tick + full TH/EN UI

- `Message 1..4` are four independent status messages, not lines of one status.
- Each message has its own **Apply** button.
- The Standard status dropdown contains 50 bilingual EN/TH statuses; choosing one fills Message 1, and **Send to Camfrog** applies the selected language variant.
- Search matches English text, Thai text, and the stable status ID. Categories include availability, work/study, activities, social, and favorites.
- The favorite star saves the selected status ID in the config. JSON v1 and plain-text files can import/export the editable Presets list; imports merge and deduplicate instead of replacing existing entries.
- **Save settings** stores the selected standard status ID in config so the dropdown restores it after restart.
- Rotation source is the non-empty Message 1..4 queue.
- The first eligible message applies immediately; each later tick waits the configured interval and applies exactly one message.
- Random mode shuffles the non-empty rows and sends one row per tick, using each row once before reshuffling.
- Sequential example at 30 seconds: M1 @ 00:30, M2 @ 01:00, M3 @ 01:30, M4 @ 02:00.
- Consecutive Camfrog send attempts are separated by at least `advanced.minimum_interval_seconds` (default 5 seconds); an early send waits instead of being dropped.
- Daily schedule and overnight quiet hours use local Windows time. A rotation tick outside the allowed window is skipped; rotation resumes on the next eligible tick.
- The sender writes once, verifies the Camfrog status Edit before commit, then sends one Enter. It does not type the payload again, send Enter to the parent combo, or click another control. The client/server acceptance is not independently observable, so the success message describes the verified field and Enter action rather than server publication.
- The verified UIA path focuses Camfrog after the single text write, waits 0.45 seconds, and sends one real Enter. If UIA cannot verify the text, the default is to skip commit; the optional coordinate fallback can be enabled separately.
- Ctrl+C/V/X/A work in the Entry and Text editors; paste replaces the selected range at its start.
- TH/EN switching now covers the main application labels, buttons, automation controls, units, modes and primary runtime state text.
- Random Color, Custom Color, and Marquee remain optional and transform only the single message being applied on that tick.

## Repository engineering and policy

The application shares the zcsc repository's security and change-management baseline:

- [Agent contract](AGENTS.md), [contribution guide](CONTRIBUTING.md), [security policy](SECURITY.md), and [release guidance](docs/release.md).
- [Repository validator](scripts/validate_repo.py) checks required project files and local Markdown links.
- [ZEAZ execution framework](ZEAZ-INTRODUCTION.md) and [AI playbooks](docs/ai/README.md) describe the repository's reusable engineering workflow.
- GitHub Actions run the repository baseline and the Windows application checks/build. Workflow artifacts are CI output; local ignored `build/` and `dist/` contents are preserved separately.

Reverse-engineering notes live in [docs/reverse-engineering](docs/reverse-engineering/), and the proposed optional [UAB integration design](docs/UAB-ZCSC-INSTALLER-DESIGN.md) has not been implemented or installed.
