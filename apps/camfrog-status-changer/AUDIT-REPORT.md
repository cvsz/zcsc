# Audit Report

## Fixed defects captured during development

- UI capture work was moved off the Tk UI thread to prevent Not Responding states.
- Background Win32 sends were bounded to prevent indefinite hangs.
- Generic `CButtonTS` commit guessing was removed after it opened unrelated browser/link actions.
- UIA wrapper misuse (`ComboBoxWrapper.set_edit_text`, wrapper `child_window`) was removed.
- Foreground fallback and background-only toggles were made mutually exclusive and switchable.
- Registry/history values are filtered and user dialogs show real status text instead of raw registry paths.
- Rotation semantics were hardened to one message per interval.
- Ctrl+V double-paste was fixed by avoiding stacked default/custom paste execution.
- Style callbacks were corrected and marquee no longer depends on leading spaces.
- Unsupported custom-status color markup was removed; Unicode markers are used instead.

## Remaining high-risk uncertainty

The exact Camfrog internal commit/publish path is not yet runtime-verified end to end. Static analysis identifies `Messages::ChangeStatus`, `SetSelfStatus`, and `CSPacket020401.text_status`, but the application deliberately does not invoke unverified internal RVAs.
