# Camfrog CSPacket020401.text_status — Static Reverse Engineering

Target: `Camfrog Video Chat.exe`

SHA-256: `0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06`

Image base: `0x140000000`

## Confirmed protobuf serializer

Serializer function starts at approximately `VA 0x141E61BB0` (`RVA 0x1E61BB0`).

### Field #1

- Wire tag: `0x08`
- Protobuf field number: `1`
- Wire type: `0` (varint)
- Object offset: `+0x18`
- Serialized only when non-zero.
- Semantic field name is not recovered from static strings in this build. It is likely status-related, but that name is **not confirmed**.

### Field #2 — `text_status`

- Qualified name string: `proto.client.user.CSPacket020401.text_status`
- Wire tag: `0x12`
- Protobuf field number: `2`
- Wire type: `2` (length-delimited)
- Object storage: tagged/Arena string pointer at `+0x10`
- Serializer code around: `VA 0x141E61C40–0x141E61CC5`
- Direct schema/name xref: `VA 0x141E61C4A` → `0x142B5CFC0`

The fast serialization path emits:

```asm
mov byte ptr [rbx], 0x12     ; field 2, wire type 2
mov [rbx+1], length          ; fast path for length < 128
...                          ; copy status bytes
```

Longer strings go through the generated protobuf helper path.

### Field #3

- Wire tag: `0x18`
- Protobuf field number: `3`
- Wire type: `0` (varint/bool)
- Object offset: `+0x1C`
- Serializer normalizes it to `0/1` using `setne`.
- Therefore the field is a protobuf `bool` (or bool-like generated representation).
- Semantic field name is not recovered from static strings in this build.

## Confirmed protobuf parser

Parser function begins around `VA 0x141E61920` (`RVA 0x1E61920`).

It explicitly recognizes only:

- `0x08` → field #1 → stores varint at object `+0x18`
- `0x12` → field #2 → parses a length-delimited string into object `+0x10`
- `0x18` → field #3 → parses varint and stores boolean at object `+0x1C`

All other protobuf tags are routed through the generic unknown-field parser.

This is strong static evidence that this Camfrog build's compiled `CSPacket020401` schema has **exactly three known fields**.

## Object layout inferred from generated protobuf code

Approximate generated message layout relevant to the fields:

```cpp
struct CSPacket020401_like {
    void* vtable;                 // +0x00
    UnknownFields/Arena meta;     // +0x08
    ArenaStringPtr text_status;   // +0x10   field #2
    int32_or_enum field_1;        // +0x18   field #1
    bool field_3;                 // +0x1C   field #3
    int cached_size;              // +0x20
};
```

The exact C++ types/names for fields #1 and #3 remain unconfirmed.

## Color/style conclusion

For `CSPacket020401` in this exact binary:

- No known protobuf field exists for text color.
- No known protobuf field exists for marquee/animation style.
- No parser branch exists for additional compiled fields beyond #1/#2/#3.
- `text_status` is serialized as an ordinary length-delimited byte string.

Therefore BBCode/HTML-like values such as `[color=#FF0000]...[/color]` are merely text unless another application layer interprets them; `CSPacket020401` itself does not encode a color attribute.

A marquee effect likewise cannot be encoded as a style flag in this packet. It can only be emulated by sending changing `text_status` strings over time, unless a different protocol packet/feature is discovered.

## Related packet: CSPacket020402.custom_status

The binary contains:

`proto.client.user.CSPacket020402.custom_status`

The serializer at approximately `VA 0x141E813B0` writes `custom_status` as **field #6** (wire type 2). The same packet also contains many other profile fields. Static qualified strings include:

- `CSPacket020402.nick`
- `CSPacket020402.alias`
- `CSPacket020402.country_code`
- `CSPacket020402.custom_status`
- `CSPacket020402.ImSkin`
- `CSPacket020402.room_subscription_level_name`

No qualified `CSPacket020402.*color` or `*.marquee` field was found.

This supports the conclusion that custom status content itself is still plain text in this build.

## High-value dynamic validation

To confirm runtime values without extracting credentials:

1. Break at module RVA `0x1E61BB0` (serialize entry).
2. Commit a unique status such as `CF_RE_020401_8F31` through Camfrog UI.
3. Inspect the object passed as `RCX`:
   - `+0x18` = field #1
   - `+0x10` = text_status string holder
   - `+0x1C` = field #3 bool
4. Compare with a normal `Available` status and with an empty custom status.
5. Record only these status-related fields and call stack RVAs.

This will reveal the semantics of fields #1 and #3 without touching authentication/session data.
