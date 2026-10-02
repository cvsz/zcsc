# Camfrog Text Over Video — Reverse Engineering Notes

Target: the active Windows installation of `Camfrog Video Chat.exe`.

- Format: PE32+ x86-64
- SHA-256: `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`
- The checked-out `build/Camfrog Video Chat.exe` is a different PE32 x86 binary from 2011 (SHA-256 `cdbf2260eb677a5efd3e74be4dacd7f90febc982da13bddcd3227b7d5f9a8d11`). Do not apply the x64 addresses below to that legacy file.

## Confirmed internal setting names

| UI meaning | Persistent/internal key | UI control id |
|---|---|---|
| Enable Text Over Video | `TOV_Enable` | `tov_enable_button` |
| Text | `TOV_Text` | `tov_text_edit` |
| Background color | `TOV_BackgroundColor` | `tov_background_color_combo` |
| Text color | `TOV_TextColor` | `tov_text_color_combo` |
| Font name | `TOV_FontName` | `tov_font_button` / font dialog |
| Font size | `TOV_FontSize` | font dialog |
| Bold | `TOV_Bold` | font dialog |
| Italic | `TOV_Italic` | font dialog |
| Horizontal alignment | `TOV_HorizontalAlignment` | `tov_horz_alignment_combo` |
| Vertical alignment | `TOV_VerticalAlignment` | `tov_vert_alignment_combo` |
| Transparency | `TOV_Transparent` | `tov_transparent_slider` |
| Migration marker | `TOV_MigratedFromCF6` | internal only |

Other confirmed TOV resources include `tov_video_animations`, `tov_video_bg`, `tov_video_bg2`, `tov_video_empty_img`, `text_over_video`, `text_over_video_state`, and `set_text_over_video_button`. The string `vwmenu_text_over_video_settings` cited in an earlier note was not found in a UTF-16 string scan of the exact binary hash above; treat it as unverified or version-specific.

## Static code anchors

The setting-name strings are registered/referenced sequentially in the same code cluster:

- `TOV_Enable` string VA `0x1426AC798`; reference at `0x140A04A81`
- `TOV_Text` string VA `0x1426AC7D8`; reference at `0x140A04B9B`
- `TOV_FontName` string VA `0x1426AC810`; reference at `0x140A04CDE`
- `TOV_Italic` string VA `0x1426AC848`; reference at `0x140A04E21`
- `TOV_Bold` string VA `0x1426AC860`; reference at `0x140A04F3B`
- `TOV_FontSize` string VA `0x1426AC878`; reference follows in the same cluster
- `TOV_BackgroundColor` string VA `0x1426AC898`; reference follows in the same cluster
- `TOV_TextColor` string VA `0x1426AC8F8`; reference follows in the same cluster
- `TOV_HorizontalAlignment` string VA `0x1426AC948`; reference follows in the same cluster
- `TOV_VerticalAlignment` string VA `0x1426AC9B0`; reference follows in the same cluster
- `TOV_Transparent` string VA `0x1426ACA18`; reference follows in the same cluster

This strongly indicates one coherent settings schema/binding block rather than unrelated strings.

### Static descriptor IDs

A second disassembly pass followed the descriptor constants passed after each key in the same registration block (`0x140A04967` onward):

| Setting key | Internal descriptor constant |
|---|---:|
| `TOV_MigratedFromCF6` | `0x615` |
| `TOV_Enable` | `0x616` |
| `TOV_Text` | `0x01000617` |
| `TOV_FontName` | `0x01000618` |
| `TOV_Italic` | `0x619` |
| `TOV_Bold` | `0x61A` |
| `TOV_FontSize` | `0x61B` |
| `TOV_BackgroundColor` | `0x61C` |
| `TOV_TextColor` | `0x61D` |
| `TOV_HorizontalAlignment` | `0x61E` |
| `TOV_VerticalAlignment` | `0x61F` |
| `TOV_Transparent` | `0x620` |

The text and font descriptors carry a different high-byte flag in this internal schema. These constants identify registration entries; they do not by themselves prove the persisted Windows registry types or color/alignment encodings. Only `TOV_Transparent` has a confirmed live `REG_DWORD` value so far.

## Capture pipeline anchors

ASCII symbol/string `SetTextOverVideo` is present at VA `0x1426742D0`, referenced around `0x1408B91B9`.

Logging strings:

- `Enabling capture TOV` at VA `0x142742E10`
- `Disabling capture TOV` at VA `0x142742E28`

Both are referenced from the function around `0x14104DED0`. That function takes an enable/disable byte and dispatches into the active capture path, so TOV is applied in the local video-capture/render pipeline, not through the custom-status protobuf path.

## Important architectural conclusion

`Text Over Video` and `Custom Status` are separate features.

- Custom status goes through status/message/protobuf paths such as `CSPacket020401.text_status`.
- Text Over Video has its own `TOV_*` settings and a capture/render hook (`SetTextOverVideo`, `Enabling capture TOV`, `Disabling capture TOV`).

Therefore the color controls shown in Camfrog Settings are **not evidence that custom status text supports color**. They style text rendered over the outgoing video frame.

## Storage

Static analysis confirms stable logical names (`TOV_*`). The live scan below confirms registry backing only for `TOV_MigratedFromCF6` and `TOV_Transparent` in the checked profile; use `scan_tov_storage.ps1` to inspect additional values read-only before integrating them.

### Read-only scan result (2026-10-01; rechecked 2026-10-02)

The scan of the active Camfrog profile found only these matching values under its video settings key:

| Value | Type | Observed value |
|---|---|---:|
| `TOV_MigratedFromCF6` | `REG_DWORD` | `1` |
| `TOV_Transparent` | `REG_DWORD` | `128` |

No `TOV_Enable`, `TOV_Text`, color, font, or alignment values were observed. The first file scan falsely listed its own script; the scanner now excludes both the script and its output, and the repeat scan found zero candidate files. This is evidence only for the profile and storage locations that the scanner checked; it does not prove those settings are absent from every Camfrog build or profile. No persistent values were written.

A targeted repeat on 2026-10-02 found the same two values under `HKEY_CURRENT_USER\Software\Camfrog\Client\<profile>\Settings\Video`; the profile name is omitted. A read-only UI Automation scan of the active main window found no TOV controls. A navigation probe found that the main-window controls are owner-drawn with blank accessible names; opening control ID `1454` and scanning Camfrog-owned popups exposed no Settings/TOV label. The TOV dialog was not reached by that automated probe, and no values were changed during it. The exact binary's UTF-16 strings also did not contain `vwmenu_text_over_video_settings`.

The user-provided 2026-10-02 recording later showed the settings dialog and preview interaction. It visibly demonstrated enabling TOV, editing sample text, opening both color pickers, choosing horizontal/vertical alignment, moving the transparency slider, opening the font dialog, and returning to the preview with Apply visible. This confirms the visible UI flow only; it does not identify UI Automation selectors, stored types/encodings, restart persistence, or rendering in an outgoing stream.

The companion app's **Inspect visible Camfrog Settings controls** action reads metadata only from visible windows owned by Camfrog processes. It scans all Camfrog PIDs, does not require an exact Settings window title, and prefers windows with a Settings title or known TOV control markers. If UI Automation exposes no such markers, it saves sanitized Camfrog window metadata for diagnosis. Only allowlisted static labels are recorded; unknown window/control titles and Edit/ComboBox values are omitted. The inspector does not click controls or write Camfrog settings. The resulting `tov-uia.json` must be inspected before exposing editing controls.

The actual type and encoding of the missing fields remain unknown. Keep TOV editing disabled and do not write guessed registry values based on this partial scan.

Do not write values until the actual backing store and value types are observed. Colors may be packed integer/COLORREF/ARGB values, alignment may be enums, and transparency may have an implementation-specific range.

## Recommended dynamic validation

1. Run `scan_tov_storage.ps1` and save baseline JSON.
2. Change exactly one Camfrog setting, e.g. Text color red -> blue, and click Apply.
3. Run the scanner again.
4. Diff the JSON outputs.
5. Repeat for Background, Horizontal Alignment, Vertical Alignment, Transparency, Font, Enable.

This differential method identifies exact paths, types, and encodings without guessing.

## Safe integration target

Once storage types are confirmed, a controller can expose:

- enable/disable TOV
- overlay text
- background color
- text color
- font name/size/bold/italic
- horizontal/vertical alignment
- transparency

Applying live changes may still require either Camfrog's normal settings Apply flow or the internal capture TOV refresh path. Do not assume changing persistent storage alone refreshes an already-active capture session.
