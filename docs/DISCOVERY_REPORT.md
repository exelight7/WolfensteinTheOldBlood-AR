# Discovery report

## VERIFIED locally — 2026-10-15

- Steam app 350080 manifest reports build 616161, English, installed state 4.
- `base/` includes chunk pairs 0, 1, 2, 3, 5, 6, 7 and 8; also master.index, streamed.resources and english.streamed.
- chunk0.resources: 139827300 bytes; SHA-256 `7a76fa93c0f122c556dcf8eeac94630a1d4a657db94c57cc15e41c506735e5b4`.
- chunk0.index: 4409293 bytes; SHA-256 `3aa93b17e2d2167e686758428bdcc84c1895b61f1512a01814f0e62314cba750`.
- Loose `graphicsdriverwarningloc.json` is another localization candidate; do not assume archive tables cover every player-visible string.

## Research leads — UNVERIFIED against installed bytes

https://github.com/Nazar-Okruzhko/ID-Tech-5 describes mixed-endian index records and raw DEFLATE payloads. Extraction support does not establish safe repacking.

https://www.nexusmods.com/wolfensteintheoldblood/mods/10?tab=description reports 3572 table entries, PUA Thai font handling and replacement of chunk0.resources/chunk0.index. These are author claims, not our measured corpus or evidence of Arabic support. No mod assets were downloaded.

## Unknowns

Localization resource names, encoding, source IDs, duplicate counts, actual total corpus, font formats/metrics/atlases, engine shaping, RTL and wrapping, dependency/index integrity, supported rebuild and distribution method. No successful in-game experiment exists.
