# Architecture

```text
GUI (CustomTkinter)
  -> Controller
     -> Camfrog detector / native profile
     -> UIA direct edit/value path
     -> bounded Win32 background path
     -> explicit foreground fallback
  -> Rotation worker
  -> Config/logging/startup/tray
  -> Registry history reader (read-only)
```

## Status evidence levels

1. Editor staged.
2. Local control committed/read-back.
3. Client publish path observed by runtime tracing.
4. Independent session/account observes the server-visible status.

Only level 4 is sufficient for an end-to-end success claim.

## Known native profile

The analyzed Camfrog x64 build is fingerprinted in `camfrog/native_profile.py`. Known classes include `CComboBoxTS`, `CEdit4ComboInnerTS`, and `CButtonStatusTS`. Diagnostic RVAs are stored but not directly invoked.

## RE summary

- `CSPacket020401.text_status`: protobuf field #2/string.
- Known parser tags: `0x08`, `0x12`, `0x18`.
- No verified custom-status color/marquee field in packet 020401.
- Text Over Video is separate and exposes `TOV_*` text/background color, font, alignment and transparency settings.
