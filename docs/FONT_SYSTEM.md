# Font system discovery

Six font-type records and associated materials/atlases were extracted from chunk0. Metrics payloads begin `idf+`; paths end `64_df.dat`. Atlas paths end `.bimage`. The `df` naming suggests distance-field rendering, but this interpretation is UNVERIFIED.

Glyph records, character map, kerning data, texture format, native Arabic coverage, runtime shaping and fallback font selection are UNVERIFIED. Do not build a production font by guessing field meanings from the signature alone. Require field-level round-trip validation on all six metrics resources and corresponding texture inspection.

IBM Plex license text is preserved; font binaries have not been downloaded or modified. A modified derivative must respect the reserved name Plex and retain OFL licensing.
