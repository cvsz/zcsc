# Camfrog Video Chat — Static Feature Inventory

## Target and method

- File: active Windows installation of `Camfrog Video Chat.exe`
- Version resource: Camfrog Video Chat `8.5.0.51219`
- SHA-256: `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`
- The checked-out `build/Camfrog Video Chat.exe` is a different 32-bit 2011 binary and is not the target for these offsets.
- Analysis: PE imports, resource metadata, embedded HTML/JavaScript, strings, and the existing protobuf notes.
- Execution: static analysis did not launch the executable. A user-provided recording dated 2026-10-02 shows the Camfrog Settings → Video & Audio → Text Over Video page and its preview, but does not identify the executable hash. This inventory does not prove that a static string is reachable, that a server accepts an operation, or that the current account has permission.

## Feature evidence

| Area | Static evidence | Confidence and limits |
|---|---|---|
| Chat and IM | `IM chat - privacy` near file offset `0x265f890`; send/delivery status strings near `0x25f56d8` and `0x25f5758`; HTML resource #211 contains message and P2P-request templates. | Direct evidence that chat/IM UI and message states are present. Runtime behavior was not tested. |
| Rooms | `Room Join`, `Join room dialog`, `Room browser`, and `Room category page` near `0x2636f28–0x2637050`; room browser HTML resource #500 at `0x34642c8`. | Direct evidence of room browsing/join UI. It does not establish stable UI Automation selectors or an automation API. |
| Audio, video, and P2P | Audio/video capture and preview strings near `0x27413b8–0x27419d8`; HTML #211 contains incoming/outgoing P2P request templates; `send_udp_p2p_packet` is present in `cmnetlite`. | Direct evidence of compiled media/P2P features. No call, device, or network behavior was exercised. |
| Profiles and accounts | `showRoomProfile`, `openRoomProfile`, `ProfileInfo`, and social-account binding/error strings near `0x267c218`, `0x2722170`, and `0x261f8e8`. | Direct evidence of profile/account-related code paths. It does not establish concurrent-account support or safe profile isolation. |
| Gifts and subscriptions | `sendGiftToRoom`, `gift_name`, `gift_price`, and subscription strings near `0x267c228`, `0x2710b18`, and `0x2710bb8`; HTML #212 styles supporter/fan tiers. | Direct evidence of gift/subscription UI metadata. A relationship to an actual payment flow is not established here. |
| Moderation and room roles | `moderation_tools`, `moderator`, `owner`, `/ban`, `/kick`, `/blockmic`, `/unblockmic`, and report/block menu strings near `0x261f130`, `0x26666c8–0x26666e0`, and `0x2666300–0x2666368`. | Direct evidence that moderation-related UI/commands exist. Role checks, command semantics, and server authorization were not validated. |
| Settings and Text Over Video | `TOV_*` settings, `SetTextOverVideo`, and capture-path strings are documented in [TEXT-OVER-VIDEO-RE.md](TEXT-OVER-VIDEO-RE.md). | The text/background color settings belong to the video overlay feature, not the custom-status packet. Do not treat them as custom-status color support. |
| Updates, ads, and support | Updater/version-check, feedback, bug-report, and ads/consent SDK strings appear in the executable; resources include ad-frame HTML. | Direct evidence of related UI/SDK code. No request, data transfer, or service interaction was performed. |
| Custom status | `CSPacket020401.text_status` is field #2 and is serialized as an ordinary string; see [CSPacket020401-RE.md](CSPacket020401-RE.md). | Strong static evidence for a text payload. No color or marquee field was found in this packet. A different rendering layer may still interpret text markup, but that is unverified. |

## Current companion-app coverage

| Requested capability | Current state in this repository |
|---|---|
| Custom status from history | History discovery is read-only; the user explicitly imports discovered values into presets. |
| Standard status catalog | 50 bilingual EN/TH entries, searchable by either language, filterable by category/favorite, and saved by stable ID. |
| Preset file exchange | JSON v1 and one-status-per-line TXT import/export; imported values merge with deduplication. |
| Message rotation | Sequential or shuffled non-empty rows; the first eligible row applies immediately, then one row per configured delay. Status writes and Enter commits are serialized by the rotation worker. |
| Rotation windows | Optional local-time daily schedule and overnight quiet hours; ineligible ticks are skipped. |
| Status submission | One verified UIA text write, a 0.45-second settle, and one foreground Enter on the same editor. Server acceptance is not independently confirmed. |
| Marquee status | Emulated as repeated status updates: a manual run advances frames at the configured frame interval; during rotation, it advances the current row until that row's rotation interval expires. Each frame is a separate status send. Automated tests cover frame scheduling; continuous rendering or server acceptance was not verified. |
| Custom status color | Custom and random color options wrap the status text in configured markup. The target binary has no confirmed color field, so visible coloring is unverified and markup may be displayed literally. |
| Start Camfrog | The helper can start Camfrog on demand when a status apply needs a client. “Start with Windows” starts the helper, not a separate Camfrog login for each account. |
| Auto respond | Optional, disabled-by-default monitor for configured private-chat and room-chat UIA controls. It parses only newly appended visible `sender: message` lines, ignores the configured own nickname, preserves non-empty drafts, and submits through an explicit UIA InvokePattern. The user must configure exact window-title fragments and control IDs. Server acceptance and current-build selectors are not verified. |
| Public web profiles | The companion app stores a nickname and opens its URL-encoded public profile, copies that link, or opens the official profiles/leaderboard directory in the user's default browser. Sign-in and profile edits remain on the official website; this app does not access credentials, cookies, or profile APIs. |
| Room event notifications | Optional, disabled-by-default phrase matching against newly appended visible room-history lines. The in-memory activity view keeps only the room title and matched phrase; raw chat lines are not persisted. This does not semantically identify membership/role events, and exact selectors/current-build behavior remain unverified. |
| Multiple online accounts | Not implemented. The controller currently selects from Camfrog processes without profile-to-sandbox identity mapping. |
| Auto-join a room | Not implemented. Static room strings are not sufficient to automate the flow safely; visible controls and a specific room target must be mapped. |
| Owner/moderator automation | The companion app supports configured `/` command templates for `op`, `friend`, `admin`, `owner`, `mute`, `kick`, and `ban`, sent through configured visible Room chat UIA controls. Published forms support `/oplist add {username}`, `/oplist add {username} friend`, `/blockmic {username}`, `/kick {username}`, and `/ban {username}`. `admin` syntax is not established by the published guide; `owner` assignment includes a password parameter and is not preconfigured. Manual commands, bad-word monitoring, and room-event notifications are pinned to one exact configured room title. Read-only inspection found the room history and composer host both use Automation ID `1002`; history can be selected by visible message-line shape, but the composer cannot be selected uniquely by ID. The adjacent candidate Send control is ID `1307`, but it is unnamed, disabled while the composer is empty, and exposes no UIA `InvokePattern` in that state. The Windows config leaves input/send selectors unset, so command submission remains unverified and no room action was sent. Source defaults remain generic and disabled. |
| Text Over Video styling | A user-provided recording visually confirms the enable checkbox, overlay text, background/text color pickers, horizontal/vertical alignment, transparency slider, font dialog, preview, and Apply button. The app now has a read-only UIA inspector for the open settings dialog. Saved value formats, stable selectors, restart persistence, and outgoing-video rendering remain unverified. |

### Live status-style probe (2026-10-02)

The active Camfrog binary matched the reviewed x64 profile. UI Automation found the `CComboBoxTS` status control and one child `Edit`. A combined color-markup/marquee payload was read back before one foreground Enter; the field then read back empty, matching its original empty baseline. The empty baseline and foreground were restored. This is consistent with the edit being consumed on commit, but it does not prove server acceptance or rendered color. The background fallback now follows the same one-write/one-Enter rule and does not require the field to retain text after Enter, preventing a consumed value from being typed again. A follow-up opened the account profile view and found no matching marker through UI Automation. No second Camfrog client was used. No TOV setting was changed during that automated probe.

The earlier automated probe did not reach the TOV dialog; it found blank accessible names on owner-drawn controls and no Settings/TOV menu label after opening control ID `1454`. The later user-provided recording reaches the page and shows the preview changing as controls are changed, ending with the Apply button visible. The recording does not provide UIA identifiers, stored value types, or post-restart evidence. The new inspector writes only sanitized control metadata to `tov-uia.json`; it omits Edit/ComboBox values and does not modify settings.

### User-provided Text Over Video recording (2026-10-02)

The recording shows the operator opening Camfrog Settings → Video & Audio → Text Over Video, enabling the feature, entering sample text, using both color pickers, selecting horizontal and vertical alignment, adjusting transparency, opening the font dialog, and returning to the preview with the Apply button visible. The preview visibly reflects the overlay text and placement. This is direct visual evidence for the settings page and preview interaction, but it does not establish the recording's Camfrog binary hash, stable UI Automation selectors, saved registry/file encodings, persistence after restart, or output in an active outgoing video stream.

## Safe integration boundary

The companion app should continue to use Camfrog's visible UI and Windows UI Automation/Win32 controls. Do not invoke discovered internal RVAs, synthesize protocol packets, reuse login/session material, or treat a role-related string as proof of permission. Room actions must use controls Camfrog itself exposes to the current signed-in account and should be individually configurable.

Concurrent account support needs an explicit isolation design and a way to map each isolated client to its own process/window. A profile record alone is not process isolation. The existing source has no such mapping yet.

## Documented server command forms

The following forms come from Camfrog's published server-command guide, not from speculative binary offsets:

| Command family | Published form or example | Notes for this app |
|---|---|---|
| Room settings | `/setopt topic <text>`, `/setopt moderator on|off`, `/setopt talk_time <seconds>`, `/setopt max_connections <count>`, `/setopt no_bots on|off`, `/setopt motd <text>`, `/setopt motd_agree on|off`, `/setopt cams_only on|off`, `/setopt password <password>`, `/setopt password_enabled on|off`, `/setopt nospam on|off`, `/setopt teens_only on|off`, `/setopt punish_timeout <seconds>` | These change room-wide settings. The companion app does not expose them. Never put a room password in a saved template. |
| Operator list | `/oplist add <nickname>`, `/oplist add <nickname> friend`, `/oplist add <nickname> owner <password>`, `/oplist remove <nickname>`, `/oplist list` | The first two forms map to the app's `op` and `friend` templates. Owner assignment contains a password argument and is not preconfigured. The guide does not establish an `admin` role form. |
| Friends | `/addfriend <...>`, `/delfriend <...>` | Separate server friend-list commands; not configured by the companion app. |
| Moderation | `/kick <nickname> [reason]`, `/ban <nickname>`, `/banip <nickname>`, `/punish <nickname> <duration> [reason]`, `/unpunish <nickname>`, `/punishlist`, `/blockmic <nickname>`, `/unblockmic <nickname>` | The app's `kick`, `ban`, and `mute` templates use documented forms. `mute` means blocking the microphone, not muting room text. |
| Bans and access list | `/banlist list [part]`, `/banlist add deny|allow nick <nickname> ...`, `/banlist add deny|allow ip ...`, `/banlist add deny|allow nick_ip ...`, `/banlist remove <rule_part>`, `/clearbl` | These may change persistent room access. Not exposed by the companion app. |
| Other published commands | `/help`, `/ver`, `/msg <nickname|group> <message>`, `/stat`, `/stats`, `/ignore <nickname>`, `/quit`, `/exit`, `/ip <nickname>`, `/whowatching <nickname>`, `/watchlist <nickname>`, `/topic <text>`, `/notopic`, `/moderator` | These are not exposed as companion-app automation actions. |

Camfrog documents different privileges for members, friends, moderators, admins, and owners. Published syntax does not prove the current account's role, current-client behavior, or server acceptance. See [Camfrog Server Commands](https://www.camfrog.com/en/server-commands.phtml) and [Camfrog moderator levels](https://help.camfrog.com/support/solutions/articles/47001150603-what-are-the-different-moderator-levels-).

## Legacy binary string scan

The supplied `build/Camfrog Video Chat.exe` is a 32-bit PE with a PE timestamp of 2011-06-07 09:51:08 UTC and SHA-256 `cdbf2260eb677a5efd3e74be4dacd7f90febc982da13bddcd3227b7d5f9a8d11`. A read-only ASCII/UTF-16 string scan found these command-like strings:

| File offset | Extracted string | Confidence |
|---|---|---|
| `0x485910` | `/kick %s` | Clear nickname format string; official guide independently documents `/kick <nick> [reason]`. |
| `0x485924` | `/ban %s` | Clear nickname format string; official guide independently documents `/ban <nick>`. |
| `0x485944` | `/banip %s` | Clear nickname format string; official guide independently documents `/banip <nick>`. |
| `0x4859a4` | `/blockmic %s` | Clear nickname format string; official guide lists block-microphone. |
| `0x485984` | `/unblockmic %s` | Clear nickname format string; official guide lists unblock-microphone. |
| `0x485970` | `/punish ` | Command prefix only; the arguments are not in this string. The official guide documents the nickname/duration/reason form. |
| `0x485958` | `/unpunish ` | Command prefix only; the official guide documents `/unpunish <nick>`. |
| `0x4858e0` | `/ignore %s` | Clear nickname format string. |
| `0x4858c4` | `/ignore %s -` | Clear nickname plus removal suffix string. |
| `0x4858f8` | `/msg %s %s` | Clear two-argument format string; official guide documents recipient and message forms. |
| `0x485934` | `/ip %s` | Clear nickname format string; command may return sensitive network information. |
| `0x480844`–`0x480898` | `/offline`, `/online`, `/busy`, `/away`, `/invisible`, `/privacy` | Command-like account-state strings; the scan alone does not prove their execution path or server behavior. |
| `0x485c8c`, `0x485ca4` | `/NOTIFYON`, `/NOTIFYOFF` | Notification-state strings; execution behavior was not traced. |
| `0x4808ac` | `/exit` | Command-like string; behavior was not traced. |

This is a string scan of the legacy 32-bit file, not a complete command grammar or a dynamic trace. It does not show which UI action consumes a string, whether it is reachable, or whether a current server accepts it. Commands documented on the current website but absent from this old file's string results are listed above as documentation evidence only.

## Additional candidate features

These are candidates, not implemented or runtime-verified capabilities:

- Per-account status presets, rotation schedule, and history import.
- Room auto-join with bounded retry after a normal Camfrog reconnect.
- Owner-configured room title/rules/welcome text through visible Camfrog settings.
- Semantic new-member and moderation-event detection (current room notifications only match configured visible text phrases).
- A per-account tray status, pause/resume, and schedule/quiet hours.
- Editable Text Over Video controls after UIA selectors and backing-store/apply behavior are verified read-only.
