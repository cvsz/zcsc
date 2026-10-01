# Camfrog Text Over Video — Reverse Engineering Notes

Target: `Camfrog Video Chat.exe`

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

Other confirmed TOV resources include `tov_video_animations`, `tov_video_bg`, `tov_video_bg2`, `tov_video_empty_img`, `text_over_video`, `text_over_video_state`, `set_text_over_video_button`, and `vwmenu_text_over_video_settings`.

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

The binary confirms stable logical names (`TOV_*`) but static analysis alone does not yet prove the exact per-user backing store on this installation (registry vs another config layer). Use the included `scan_tov_storage.ps1` on the Windows host to discover the concrete values read-only.

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
