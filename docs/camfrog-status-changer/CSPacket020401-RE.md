# CSPacket020401.text_status reverse-engineering summary

Analyzed client fingerprint: `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`.

## Verified static findings

- `proto.client.user.CSPacket020401.text_status` exists in the client.
- `text_status` is protobuf field **#2**, wire type **2** (length-delimited string), tag `0x12`.
- The analyzed parser recognizes `0x08`, `0x12`, and `0x18` as known tags for this packet.
- No verified `color`, `font_color`, `style`, `marquee`, `speed`, or `direction` field was identified in `CSPacket020401`.
- Static serializer anchor for text status is recorded as diagnostic RVA `0x1E61C40`.

## Consequence

Custom-status styling such as `[color=#FF0000]...` or HTML marquee markup should not be treated as protocol-supported. Marquee behavior must be implemented as repeated plain-text status frames unless future runtime/protocol evidence proves otherwise.

RVA values are research anchors only and are not invoked directly by the application.
