# Font system discovery

Six font-type records and associated materials/atlases were extracted from chunk0. Metrics payloads begin `idf+`; paths end `64_df.dat`. Atlas paths end `.bimage`. Four English fonts receive generated Arabic distance-field glyphs.

Glyph records, sorted character maps, pair tables and the four single-image atlas layouts are parsed and round-trip checked by the local tools. Runtime fallback behavior and complete visual coverage at all sizes are not certified. See [Arabic rendering](ARABIC_RENDERING.md) for the current joining repair and its pending in-game check.

IBM Plex Arabic Regular was fetched unmodified from official IBM commit 39276912b05f700ee1dd491950c35d8697214208. TTF SHA-256: 8e0f1046c736bf939d4939ee3ae0116acf61cbcd6592deae7656761627080981. License: licenses/IBM_Plex_OFL.txt, identical to the font package license. The TTF is not modified or publicly bundled. A derivative font must respect the reserved name Plex and retain OFL licensing.

## Preliminary character-map investigation

Related-engine research: https://github.com/id-Software/DOOM-3-BFG/blob/master/neo/renderer/Font.cpp describes a different idf version, glyph records and a sorted codepoint map. It is a research lead only; no GPL source was copied or vendored.

For the local idf+ files, interpreting the big-endian u16 at byte 10 as count, skipping count * 12 bytes after the 12-byte header, and reading count little-endian u32 values yields sorted candidate codepoint maps in all six resources. Counts: 237, 233, 279, 238, 238, 2133. None contain entries in U+0600–06FF, U+FB50–FDFF or U+FE70–FEFF. This hypothesis needs field-level round-trip and visual verification; it is not yet proof of complete runtime Arabic support or its absence.

## Experimental pilot format and output

Glyph records fit little-endian `BBbbHHHh`: byte width/height, signed top/left, u16 advance/x/y, and a signed kerning-start index. The character map follows the glyph records. Remaining data is a big-endian u16 pair count plus sorted eight-byte `<HHf` entries (previous glyph index, next glyph index, adjustment). Across all 3358 original glyphs in six fonts, the final glyph field equals the first pair row for that glyph, or -1 exactly when it has no outgoing pairs. This format relationship is measured; engine lookup behavior is inferred from it.

The 2026-10-24 repair assigns those indices to appended glyphs after sorting the combined pair table. Native glyph records and pair values remain byte-identical because appended glyph indices sort after native ones. Previously leaving every appended index at -1 made the Arabic pair table unreachable in an index-based reader. Indices must fit a signed 16-bit field; -1 remains the no-pairs sentinel.

English font bimages have a 72-byte header and one raw 8-bit alpha image. Four atlas resources (book, medium, arial_black, courier) are expanded vertically; their original pixel data is byte-identical. Header image heights and payload size are updated consistently. Arabic forms are rasterized from unmodified IBM Plex Arabic at size 64 and converted to an experimental distance field with 8-pixel padding. New glyphs append at U+E000 onward, leaving original codepoint and auxiliary indices intact.

The cyrillic atlas has 11 mip levels and is excluded from the English build rather than relaxing single-image validation. Japanese resources are also unchanged. The Arabic logical source remains separate from generated presentation forms and PUA runtime data.
