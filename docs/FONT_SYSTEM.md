# Font system discovery

Six font-type records and associated materials/atlases were extracted from chunk0. Metrics payloads begin `idf+`; paths end `64_df.dat`. Atlas paths end `.bimage`. The `df` naming suggests distance-field rendering, but this interpretation is UNVERIFIED.

Glyph records, character map, kerning data, texture format, native Arabic coverage, runtime shaping and fallback font selection are UNVERIFIED. Do not build a production font by guessing field meanings from the signature alone. Require field-level round-trip validation on all six metrics resources and corresponding texture inspection.

IBM Plex Arabic Regular was fetched unmodified from official IBM commit 39276912b05f700ee1dd491950c35d8697214208. TTF SHA-256: 8e0f1046c736bf939d4939ee3ae0116acf61cbcd6592deae7656761627080981. License: licenses/IBM_Plex_OFL.txt, identical to the font package license. The TTF is not modified or publicly bundled. A derivative font must respect the reserved name Plex and retain OFL licensing.

## Preliminary character-map investigation

Related-engine research: https://github.com/id-Software/DOOM-3-BFG/blob/master/neo/renderer/Font.cpp describes a different idf version, glyph records and a sorted codepoint map. It is a research lead only; no GPL source was copied or vendored.

For the local idf+ files, interpreting the big-endian u16 at byte 10 as count, skipping count * 12 bytes after the 12-byte header, and reading count little-endian u32 values yields sorted candidate codepoint maps in all six resources. Counts: 237, 233, 279, 238, 238, 2133. None contain entries in U+0600–06FF, U+FB50–FDFF or U+FE70–FEFF. This hypothesis needs field-level round-trip and visual verification; it is not yet proof of complete runtime Arabic support or its absence.

## Experimental pilot format and output

Observed glyph records fit little-endian `BBbbHHHh`: byte width/height, signed top/left, u16 advance/x/y, signed auxiliary index. The final field is preserved for existing glyphs and set to -1 for appended glyphs (many original records use -1). Character map follows glyph records. Remaining data fits a big-endian u16 pair count plus count * 8 bytes; it is preserved unchanged. These layouts parse all six source fonts exactly; auxiliary/kerning runtime semantics still need verification.

English font bimages have a 72-byte header and one raw 8-bit alpha image. Four atlas resources (book, medium, arial_black, courier) are expanded vertically; their original pixel data is byte-identical. Header image heights and payload size are updated consistently. Arabic forms are rasterized from unmodified IBM Plex Arabic at size 64 and converted to an experimental distance field with 8-pixel padding. New glyphs append at U+E000 onward, leaving original codepoint and auxiliary indices intact.

The cyrillic atlas has 11 mip levels. Initial strict single-image validation rejected it; it is excluded from this English pilot instead of relaxing validation. Japanese resources are also unchanged. Native Arabic was not tested; pre-shaped PUA is an experimental pilot choice to obtain a first visual test, not a proven final rendering strategy.
