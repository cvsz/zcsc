# Audit Report

## Unreleased root migration audit

- Exact client process matching prevents `CamfrogStatusChanger.exe` and similarly named helper applications from making the dashboard report Camfrog as running.
- Automation now refuses ambiguous Camfrog windows and status controls. Both UIA and Win32 ambiguity paths fail closed without continuing to another guessed target.
- Fresh config defaults and registry test fixtures no longer contain account-specific status strings or contact data.
- Pillow was updated after the dependency audit reported vulnerabilities in the prior pinned version.
- The Inspect worker's exception callback now captures the error before leaving the `except` scope.
- Repository-local scripts are an explicit Python package so `tests/test_bootstrap.py` cannot resolve an unrelated installed `scripts` package.
- The Ubuntu baseline workflow again runs the full pytest suite, with application dependencies installed; it no longer narrows discovery to the bootstrap test.
- Historical release ZIPs in the former app subtree contain account-specific identity/contact strings in bundled source and bytecode fixtures. They were not copied into root `tags/`; the original Git history is unchanged by this worktree cleanup.
- The current-source repository CI sequence passes locally in an isolated Linux environment. The RC11 Windows build and full test suite also pass; the 16,430,734-byte x64 EXE and its matching manifest are in `dist/2.2.5-rc11-windows-x64/` (SHA-256 `f9546f1badd21e15b093f0dffcd880f97fd862ce53cc15fa934e63e3c31daa99`). The executable was not launched, so live Camfrog UI, status, room, and server behavior remain unverified.

## Fixed defects captured during development

- UI capture work was moved off the Tk UI thread to prevent Not Responding states.
- Background Win32 sends were bounded to prevent indefinite hangs.
- Generic `CButtonTS` commit guessing was removed after it opened unrelated browser/link actions.
- UIA wrapper misuse (`ComboBoxWrapper.set_edit_text`, wrapper `child_window`) was removed.
- Status submission now uses a foreground Enter after one verified UIA text write; the old background-only status-commit toggle was removed because Camfrog did not reliably accept a background key message.
- Registry/history values are filtered and user dialogs show real status text instead of raw registry paths.
- Rotation semantics were hardened to one message per interval.
- Auto rotation now applies the first eligible row immediately, waits the full configured delay after its Enter commit, then applies one next row per cycle.
- Camfrog status submission now uses one text write and one Enter on the verified Edit; no second Enter, selection notification, or button click is used as a commit signal.
- The optional coordinate fallback remains opt-in and is used only when UIA cannot verify the status text.
- A temporary Windows check confirmed the field still matched the single-Enter payload and that the original value was restored. This verifies local input/restore only, not server-visible status publication.
- Ctrl+V double-paste was fixed by avoiding stacked default/custom paste execution.
- Style callbacks were corrected and marquee no longer depends on leading spaces.
- Optional Random Color and Custom Color are encoded inside the outgoing status string using markup. Static analysis finds no color field in `CSPacket020401`; whether another Camfrog layer renders that markup remains unverified.
- Marquee is emulated by sending changing status strings on rotation ticks; it is not a native status animation.
- Manual room actions are configurable visible-UI commands with a confirmation on every send. Bad-word matches are limited to new visible room-history lines; kicking remains confirmation-based by default and can be explicitly enabled through the saved Auto kick setting. Automatic kicks still require a valid configured command and pass through exact-room, safe-nickname, empty-draft, and single-send checks.
- Native status fallbacks now stop after one Enter is dispatched for a text value verified before commit. They no longer retype a status when Camfrog consumes/clears the field after Enter; server acceptance remains unverified.
- The dashboard groups controls into a dedicated tab for each feature; auto-reply text preserves line breaks, and Marquee advances the selected status on a repeating interval.
- The Windows candidate embeds the supplied app icon in the executable and bundles it for the tray resource path. RC7 added a read-only Text Over Video UIA inspector; RC8 searches visible windows belonging to the configured Camfrog process and saves sanitized diagnostic metadata when UIA does not expose known TOV controls. Actual interactive control metadata, packaged startup, and live Camfrog behavior remain unverified.
- RC9 adds public Camfrog profile and directory shortcuts using the default browser. The nickname is URL-encoded as one path segment. The app does not collect credentials/cookies, scrape pages, or write profile settings; profile editing remains in Camfrog's official site.
- RC10 pins room commands, bad-word monitoring, and room-event notifications to one exact configured room title. The UI persists an owner nickname and per-action target nicknames; the owner value is not a Camfrog role or authorization check.
- Room commands and bad-word monitoring stay disabled by default in source. They need explicit enablement, verified room UIA selectors, and configured command templates.
- A static strings scan of the supplied legacy 32-bit executable found command-like templates including `/kick %s`, `/ban %s`, `/banip %s`, `/blockmic %s`, `/unblockmic %s`, `/ignore %s`, `/msg %s %s`, and command prefixes for `/punish` and `/unpunish`. Exact offsets and limits are recorded in `docs/reverse-engineering/FEATURE-INVENTORY.md`; this is not a runtime trace.
- On the Windows host, the user config was backed up and updated with the requested room-control profile; strict UTF-8 decoding and JSON parsing pass with no BOM, and the saved Thai/English terms remain intact. Room actions, bad-word monitoring, configured Auto kick, and five documented templates were retained. Read-only UIA inspection found history and composer host ID `1002`; the composer cannot be selected uniquely because that ID is shared. Adjacent Send candidate `1307` is owner-drawn and exposes no `InvokePattern` while empty, so the input/send selectors remain unset. No room command was sent.

## Remaining high-risk uncertainty

The exact Camfrog internal commit/publish path is not yet runtime-verified end to end. Static analysis identifies `Messages::ChangeStatus`, `SetSelfStatus`, and `CSPacket020401.text_status`, but the application deliberately does not invoke unverified internal RVAs.

Room-command syntax, account role, Camfrog server authorization, and kick results have not been validated in a live room. Templates are empty by default, and no moderation action should be described as server-confirmed based on UIA submission alone.
