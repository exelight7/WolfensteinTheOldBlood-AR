# Discovery report

## VERIFIED locally — 2026-10-15

- Steam app 350080 manifest reports build 616161, English, installed state 4.
- `base/` includes chunk pairs 0, 1, 2, 3, 5, 6, 7 and 8; also master.index, streamed.resources and english.streamed.
- chunk0.resources: 139827300 bytes; SHA-256 `7a76fa93c0f122c556dcf8eeac94630a1d4a657db94c57cc15e41c506735e5b4`.
- chunk0.index: 4409293 bytes; SHA-256 `3aa93b17e2d2167e686758428bdcc84c1895b61f1512a01814f0e62314cba750`.
- Loose `graphicsdriverwarningloc.json` is another localization candidate; do not assume archive tables cover every player-visible string.

## VERIFIED archive observations

The independent reader consumed all eight chunk indexes exactly (no trailing bytes), accounting for 90863 records. chunk0 has 22539 records. Index parsing alone does not validate all payloads; only 35 name-selected candidates were decoded and size-checked.

`strings/english.lang` is chunk0 entry 22456 (zero-based), offset 89773744, stored/uncompressed size 408195. Its SHA-256 is `6eeb295fffe09106c839c05fcfda8ef97913e3b0bcdee4057314135c4a7c0d1a`. UTF-8 BOM, CRLF, braced quoted key/value table, native #str_ IDs. Parsed 3572 unique IDs, 82 empty values and 241 groups sharing an identical decoded value. These are main-table counts, not proof of all player-visible text.

Six metrics resources of type `font` use the `idf+` signature: arial_black, courier, cyrillic/idakagi_semibold, futura_com_book, futura_com_medium, japanese/futura_com_medium_jpn90. Associated material and bimage atlas records were extracted locally. No glyph/atlas modification has been performed.

Compressed candidates use raw DEFLATE and end with the sync-flush marker `0000ffff`, rather than a final block. The decoder validates exact output size and adds an in-memory empty final block only at that observed boundary, then checks stream completion and rejects unused/unconsumed data. This is data decoding evidence, not proof of a valid game-side compressor.

## Experiment ARCHIVE-001 — strict final-stream requirement

- Hypothesis: compressed payloads are complete raw DEFLATE streams.
- Command: inventory command in BUILD_GUIDE.md, initial decoder revision.
- Files modified: ignored extraction outputs only; installed archives unchanged.
- Expected: declared output size and end-of-stream both satisfied.
- Actual: first compressed candidate yielded its declared 30 bytes but eof was false. Same behavior observed in all sampled font resources.
- Follow-up: terminal sync-flush marker observed. A synthetic Z_SYNC_FLUSH fixture reproduces it; appending an empty final block in memory permits strict completion checks. All 35 candidates now decode with exact sizes, no extraction errors.
- Conclusion: complete-stream hypothesis rejected; sync-flush-boundary decoder adopted for the observed layout. Repacking remains UNVERIFIED.

## External research leads

https://github.com/Nazar-Okruzhko/ID-Tech-5 describes mixed-endian index records and raw DEFLATE payloads. Extraction support does not establish safe repacking.

https://www.nexusmods.com/wolfensteintheoldblood/mods/10?tab=description reports 3572 table entries, PUA Thai font handling and replacement of chunk0.resources/chunk0.index. These are author claims, not our measured corpus or evidence of Arabic support. No mod assets were downloaded.

## Unknowns

Complete player-visible corpus beyond the main table, font field semantics and atlas encoding, engine shaping, RTL and wrapping, dependency/index integrity, supported rebuild and distribution method. No successful in-game experiment exists.
