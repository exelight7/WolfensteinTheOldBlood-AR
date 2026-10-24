# Arabic rendering

Arabic source stays in logical Unicode order. The build shapes and reorders it,
then maps the resulting forms to 134 appended PUA glyphs in four fonts. Earlier
menu rendering was confirmed by the owner. This does not certify every UI and
subtitle size.

## Connected-letter seams — 2026-10-24

The owner reported connected Arabic letters with small gaps. Inspection of all
3358 original glyph records across six fonts established that the final signed
16-bit field is the first outgoing kerning-pair index, or -1 when none exists.
The generated Arabic pair tables were present, but 47 glyphs in each changed
font incorrectly retained -1. Both the reviewed build and public v1.0.0 have
this defect.

`pilot_font.extend_font` now writes the pair-start indices. The independent
runtime verifier checks every glyph's index. The metrics diagnostic now follows
these indices too; its previous flat-table lookup concealed the missing links.
An index-aware offline layout model changes 2162 joins per font from zero-pixel
overlap to the intended one-pixel overlap. This explains a plausible source of
antialiasing seams; the engine's exact lookup behavior remains an inference
until the owner checks the game.

A local repair was installed on the owner's reviewed build. Only the two-byte
indices of 188 glyphs changed: no translation, atlas, advance, or existing pair
value changed. A separate full build from vanilla reproduced the same repair.
The repair is included in the 1.0.1 release packages. In-game confirmation of
the repaired result is still pending.

Local evidence is under ignored `workspace/diagnostics/font_investigation/` and
`workspace/font_joining_fix/`; the pre-install backup is
`workspace/backups/font_joining_pretest/`.

Before changing overlap or rasterization, compare the repaired build in the same
menu and subtitle scene at the same resolution. Check small text, highlights,
connected strokes, dots, and normal breaks after non-joining letters. Do not
equate the offline metric result with a real game screenshot.

Fixtures must cover Arabic-only text, Latin key E, number 25, parentheses, colon, question mark, controller placeholders, multiple lines and long subtitles. Verify dots, hamza, joining, baseline, clipping and alignment at every font size used.
