# Text Over Video reverse-engineering summary

Camfrog Settings -> Video -> Text Over Video is a separate feature from custom status.

## Verified setting/control anchors

- `TOV_Enable` / `tov_enable_button`
- `TOV_Text` / `tov_text_edit`
- `TOV_BackgroundColor` / `tov_background_color_combo`
- `TOV_TextColor` / `tov_text_color_combo`
- `TOV_FontName`, `TOV_FontSize`, `TOV_Bold`, `TOV_Italic`
- `TOV_HorizontalAlignment` / `tov_horz_alignment_combo`
- `TOV_VerticalAlignment` / `tov_vert_alignment_combo`
- `TOV_Transparent` / `tov_transparent_slider`
- runtime anchors include `SetTextOverVideo`, “Enabling capture TOV”, and “Disabling capture TOV”.

## Consequence

Text/background colors shown in the Text Over Video settings apply to text rendered over the webcam/video frame. They are not evidence that custom-status text supports font colors.

Storage/value-type mapping remains a read-only research task until runtime differential tests identify exact persistence semantics.
