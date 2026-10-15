# Font system discovery

Six font-type records and associated materials/atlases were extracted from chunk0. Metrics payloads begin `idf+`; paths end `64_df.dat`. Atlas paths end `.bimage`. The `df` naming suggests distance-field rendering, but this interpretation is UNVERIFIED.

Glyph records, character map, kerning data, texture format, native Arabic coverage, runtime shaping and fallback font selection are UNVERIFIED. Do not build a production font by guessing field meanings from the signature alone. Require field-level round-trip validation on all six metrics resources and corresponding texture inspection.

IBM Plex license text is preserved; font binaries have not been downloaded or modified. A modified derivative must respect the reserved name Plex and retain OFL licensing.

## Preliminary character-map investigation

Related-engine research: https://github.com/id-Software/DOOM-3-BFG/blob/master/neo/renderer/Font.cpp describes a different idf version, glyph records and a sorted codepoint map. It is a research lead only; no GPL source was copied or vendored.

For the local idf+ files, interpreting the big-endian u16 at byte 10 as count, skipping count * 12 bytes after the 12-byte header, and reading count little-endian u32 values yields sorted candidate codepoint maps in all six resources. Counts: 237, 233, 279, 238, 238, 2133. None contain entries in U+0600–06FF, U+FB50–FDFF or U+FE70–FEFF. This hypothesis needs field-level round-trip and visual verification; it is not yet proof of complete runtime Arabic support or its absence.
