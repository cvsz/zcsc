# CODEX-MASTER-PROMPTS.md

Audit findings and Codex work prompts for `cvsz/zcsc` (Camfrog Status Changer).

## How to use this file

1. Paste **Prompt 0** into Codex first. It sets the rules for the whole session.
2. Then paste **P1 to P7** one at a time, in order. Codex should execute one bounded item per run, then stop and report.
3. Items marked **[S]** are suspected defects. Codex must reproduce them before changing any code.

## Audit scope and limits

- **Read directly:** `README.md`, `AUDIT-REPORT.md`, `app.py`, `status_text.py`, `status_styles.py`, `registry_history_dump.py`.
- **Not readable during the audit:** `system/`, `ui/`, `camfrog/`, `tests/` (directory pages were blocked by GitHub robots rules). Findings about these areas are inferred from the README and audit report.
- **Status legend:** *Confirmed* = seen in code or in the repo's own audit report. *Likely* = strong inference from code that was read. *Suspected* = inferred from docs; must be reproduced first.

---

## Bug report

| # | Sev | Status | Where | Bug |
|---|---|---|---|---|
| 1 | High | Confirmed | `status_styles.apply_styles` | The color template is user-configurable and applied with `str.format`. If it lacks `{text}`, the user's status is silently replaced by only the markup. If it has stray braces, `format` raises, `except: pass` swallows it, and the function still returns `chosen` as if the color was applied. Format fields also allow attribute access. |
| 2 | High | Confirmed | `status_styles.marquee_frame` | After `.rstrip()`, blank frames become `""`. Rotation or marquee can then send an empty status to Camfrog, which clears it. |
| 3 | Med | Confirmed | `marquee_frame` | Slices by code point. Thai combining vowels and tone marks get split from their base consonant, so frames render as broken glyphs. |
| 4 | Med | Confirmed | `app.py:main` | `store.load()` and `startup_config.get("ui", {}).get(...)` run outside the `try`. A config with `"ui": null` or a `PermissionError` on `%APPDATA%` crashes the hidden-console build with no dialog and no log. |
| 5 | Low | Confirmed | `app.py` | `messagebox` is called before any Tk root exists, creating a stray default root (a blank "tk" window flashes). |
| 6 | Med | Likely | `registry_history_dump.py` | `path.write_text` with no `mkdir(parents=True, exist_ok=True)`; fails if the app has never run. No error handling; returns 0 on empty or failed scan. |
| 7 | Med | Confirmed | `status_text.compose_two_lines` | Hard-truncates to 2 lines while the app now has 4 independent messages. Any remaining caller silently drops lines 3 and 4. `comparable_status` also does not strip trailing NULs or normalize Unicode. |
| 8 | Low | Confirmed | `status_styles.random_color` | Duplicate helper that does not validate hex values and diverges from `apply_styles`. `int(width)` on a bad config value is uncaught. |
| 9 | High | Confirmed (per AUDIT-REPORT) | git history | The audit states old release ZIPs contain account-specific identity/contact strings and that history is unchanged. In a public repo this is a live PII leak. |
| 10 | High | Suspected | room / bad-word monitor | Lines are parsed as `sender: message`. A multi-line message can contain a second line like `VictimNick: <badword>`, so with Auto kick on, an attacker can get another user kicked. |
| 11 | High | Suspected | Auto kick | Thai has no word boundaries; substring matching over a broad catalog yields false positives. The allowlist visibly patches these one at a time. Auto kick without a prompt on top is risky. |
| 12 | Med | Suspected | `{username}` templates | Nicknames with spaces, `/`, or newlines can inject extra slash commands. The "safe-nickname" check needs adversarial tests. |
| 13 | Med | Suspected | foreground Enter | Sender focuses Camfrog, waits a fixed 0.45 s, then sends Enter. If focus is stolen, the keystroke goes to the wrong app. Needs a foreground-HWND check immediately before send. |
| 14 | Med | Suspected | coordinate fallback | DPI awareness may not be set, giving wrong coordinates on scaled displays. |
| 15 | Med | Suspected | rotation | Local-time windows and overnight quiet hours can misbehave across DST. Intervals should use a monotonic clock. |
| 16 | Low | Suspected | build / ops | `build_exe.bat` and `build_exe_fixed.bat` duplicate each other. `unlock_and_build.ps1` and the Windows startup registry entry (unquoted paths) were not reviewed. |
| 17 | Low | Confirmed | docs | README is a changelog in non-chronological order (2.0.0-rc2 and rc1 appear after 2.2.5). Template debris remains (`CLAUDE.md`, `OPENCODE.md`, `ecc-install.json`). Two PRs are open and unreviewed. |

**Legal note:** `docs/reverse-engineering` records static analysis of Camfrog's proprietary binary, including RVAs. Review against Camfrog's EULA before keeping it public.

---

## Prompt 0: master orchestrator (paste first)

```text
You are a principal Python/Windows-desktop engineer working in cvsz/zcsc
(Camfrog Status Changer, Tkinter + UIA/Win32, PyInstaller, Windows-first).

MISSION: fix the audited defects below, one bounded work item at a time, with
tests first. Never mark unverified work complete.

HARD RULES
1. Read AGENTS.md, AUDIT-REPORT.md, PRODUCTION-READINESS.md, CHANGELOG.md first.
2. No live Camfrog is available. All Windows/UIA/registry/Win32 behavior must be
   tested through fakes/mocks. Tests must pass on Ubuntu CI (no winreg/pywinauto
   import at module import time without guards).
3. Do NOT invoke discovered internal RVAs, add AV exclusions, store credentials,
   scrape sites, weaken safety defaults, or enable room commands, bad-word
   monitoring, Auto kick or auto-reply by default.
4. Do NOT rewrite git history, force-push, merge, tag, or release without
   explicit authorization. Prepare commands and a runbook instead.
5. Every defect: (a) write a failing regression test reproducing it, (b) minimal
   fix, (c) run full pytest + compileall + scripts/validate_repo.py, (d) update
   CHANGELOG.md, AUDIT-REPORT.md and tests, (e) report exactly what changed,
   results, blockers, next item.
6. Suspected defects (marked [S]) must first be confirmed by reading the code.
   If not reproducible, document "not reproducible" with evidence; don't change code.
7. Preserve public behavior and config schema; add migrations for any config change.

WORK ORDER: P1 styles/status text -> P2 startup/config/logging -> P3 moderation
parsing safety [S] -> P4 send-path/focus/DPI/rotation [S] -> P5 registry tool ->
P6 repo hygiene & history PII -> P7 CI/build.
Create/maintain exec-planning.md with ID, priority, status, dependencies, scope,
acceptance criteria, tests, security notes. Execute only the first incomplete item,
then stop and report.
```

---

## P1: styles and status text

```text
ITEM P1 — status_styles.py / status_text.py

Defects (confirmed):
D1 apply_styles: color_template.format() can drop {text} entirely, raises on stray
   braces (swallowed), still returns `chosen` after failure, and allows attribute
   access via format fields.
D2 marquee_frame + rstrip yields "" frames -> empty status can be sent.
D3 marquee slices by code point -> splits Thai combining marks (U+0E31, U+0E34-0E3A,
   U+0E47-0E4E) from base characters.
D4 random_color() duplicates/diverges from apply_styles palette handling; int(width)
   unguarded.
D5 compose_two_lines truncates to 2 lines; comparable_status ignores NUL/NFC.

Tasks:
- Replace str.format with a strict validator: template must contain exactly one
  {text} and at most one {color}; reject other fields/braces; on invalid template
  fall back to plain text AND return chosen=None. Add a config validation message.
- Make marquee grapheme-safe (segment into extended grapheme clusters; if no lib is
  available, implement a cluster function treating Thai/Unicode combining marks
  (category Mn/Mc) as attached to the previous base). Never emit a frame that is
  empty or whitespace-only: skip to the next non-blank frame; marquee never
  produces a status the caller would treat as "clear".
- Unify palette validation in one helper; coerce width with a safe default.
- Delete or deprecate compose_two_lines (grep all callers first); make
  comparable_status NUL-strip + NFC-normalize without changing existing passing cases.
Tests: property tests (hypothesis if already a dependency, else parametrized) for
Thai strings, empty/whitespace, width 4..80, multi-line, emoji, malformed templates.
Acceptance: no test or caller can obtain "" from marquee for non-blank input.
```

---

## P2: startup, config, logging

```text
ITEM P2 — app.py startup hardening

- Move configure_logging(), store.ensure_defaults(), store.load() inside guarded
  startup; derive language via a safe helper tolerant of non-dict "ui", None,
  wrong types.
- Any pre-UI failure must write to app.log (fallback: %TEMP% if APPDATA is
  unwritable) and show an error dialog.
- Create one hidden Tk root for messageboxes and destroy it; no stray window.
- Audit SingleInstance for stale-lock behavior and handle crash-leftover locks.
- Add multiprocessing.freeze_support() if any multiprocessing/spawn is used (verify).
- Verify atomic config save handles PermissionError from AV/indexer locks with
  bounded retry and no data loss; add corrupt-config recovery tests with
  valid-JSON-but-wrong-shape cases ("ui": null, list instead of dict).
Tests: simulate each failure with monkeypatch; assert exit codes and log output.
```

---

## P3: moderation parsing safety [S]

```text
ITEM P3 — room history parsing, bad-word matching, command templating  [S]

First CONFIRM by reading code (find the history parser, matcher, command builder):
a) Multi-line messages: can a continuation line like "Victim: badword" be parsed
   as a new sender line? Write a failing test with a fake history control.
b) Substring matching of Thai terms producing false positives.
c) {username} substitution with spaces, '/', newlines, leading '/', unicode
   direction/zero-width characters, very long names.

If confirmed:
- Parse history with line-structure awareness: only treat a line as a new message
  if it matches the observed row boundary signal from fixtures; otherwise append to
  the previous message. When structure is ambiguous, FAIL CLOSED (no action).
- Auto kick requires: exact room, sender matches a strict nickname regex, term
  matched with Thai-aware segmentation or explicit per-term "substring ok" flag,
  allowlist applied first, per-sender cooldown, and a max-actions-per-minute cap
  with a kill switch that disables Auto kick and logs it.
- Reject nicknames containing whitespace, control/format characters, or a leading
  '/'; render the exact outgoing command in the confirmation.
- Add a regression corpus (tests/fixtures) of false-positive and spoof cases.
- ReDoS-test every obfuscation regex with adversarial inputs and a time budget.
Never enable these features by default.
```

---

## P4: send path, focus, DPI, rotation [S]

```text
ITEM P4 — foreground Enter, coordinate fallback, scheduling  [S]

- Before the real Enter: verify GetForegroundWindow() belongs to the Camfrog
  process and the target Edit still holds the verified text; if not, abort without
  sending and surface a clear error. Replace fixed sleep with a bounded poll.
- Coordinate fallback: confirm DPI awareness (per-monitor v2 via manifest or
  SetProcessDpiAwarenessContext before Tk init) and add tests with a fake DPI layer.
- Rotation: use time.monotonic for intervals; use timezone-aware datetime for
  daily/overnight windows; test DST spring-forward/fall-back and midnight wrap.
- Verify the minimum_interval_seconds queue never drops or double-sends under
  concurrent Apply + rotation tick (stress test with fake clock).
```

---

## P5: registry tool

```text
ITEM P5 — registry_history_dump.py + camfrog/registry_status.py

- Create store.dir with mkdir(parents=True, exist_ok=True); wrap in try/except;
  nonzero exit on failure or when scanned_keys == 0 with a clear message.
- Guard winreg import so the module is importable on Linux CI; test via fake winreg.
- Add an opt-in redaction pass (emails, phone-like numbers, URLs) for the dump,
  and document that dumps contain personal text and must not be shared.
- Add tests for REG_BINARY UTF-16LE/ASCII carving with metadata prefixes, odd
  alignment, truncated blobs, and excluded-key filtering.
```

---

## P6: repo hygiene and history PII

```text
ITEM P6 — hygiene (analysis only; no history rewrite without authorization)

- Run gitleaks/trufflehog-style scanning plus grep over ALL history, including
  binary/zip blobs and .pyc, for the identity/contact strings AUDIT-REPORT mentions.
  Output a report with commit SHAs and paths only (no raw PII in the report).
- Prepare, but do not run, a git filter-repo runbook (paths/blobs to purge, force-push
  and fork/cache/PR-ref cleanup steps, contributor notification).
- Remove or relocate template debris (CLAUDE.md, OPENCODE.md, ecc-install.json) only
  if nothing references them (grep + validate_repo.py).
- Rewrite README into: current release, install/run, features, security model,
  changelog link. Move per-RC history to CHANGELOG.md in chronological order.
- Triage the 2 open PRs: summarize, check for conflicts, never merge.
- Flag the docs/reverse-engineering content for an EULA/legal review decision.
```

---

## P7: CI and build

```text
ITEM P7 — build/CI

- Diff build_exe.bat vs build_exe_fixed.bat; keep one, make the other a thin shim
  or delete; ensure the build fails on test/compile failure.
- Read unlock_and_build.ps1, run_hidden.bat/.vbs, release_manifest.ps1; fix
  quoting of paths with spaces, avoid ExecutionPolicy Bypass where unnecessary, no
  Mark-of-the-Web stripping or AV tampering.
- Quote the Windows startup registry value and test paths with spaces/Thai chars.
- Pin all dependencies with hashes (pip-compile --generate-hashes), run pip-audit,
  verify Pillow 12.3.0 exists on PyPI and has no open advisories, and add
  Dependabot.
- CI: ubuntu full pytest, windows-latest test+build, upload artifact + SHA-256
  manifest, and optional signing step gated on secrets that are absent in PRs.
- No security gate may be disabled to get green CI.
```

---

## Definition of done (all items)

- Failing regression test written first, then fixed; full pytest, `compileall`, and `scripts/validate_repo.py` pass on Ubuntu and Windows CI.
- `CHANGELOG.md`, `AUDIT-REPORT.md`, and `exec-planning.md` updated.
- No safety default weakened; moderation, Auto kick, and auto-reply remain off by default.
- Live Camfrog behavior (UIA selectors, status publication, room actions) is still reported as **unverified** unless tested on a real Windows + Camfrog setup per `PRODUCTION-READINESS.md`.