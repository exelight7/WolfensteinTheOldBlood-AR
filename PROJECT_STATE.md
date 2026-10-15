# Project state

Date: 2026-10-15

- Phase: complete text-source audit requested before any further translation. Translation gate: HOLD.
- Build: workspace/menu_pilot_ordered, 33 translated records, 73 generated Arabic forms mapped to PUA, four font/atlas pairs changed. Ordered build installed on 2026-10-15. Previous append-only build crashed and is superseded.
- Translation percentage: 0.92% of the main English table; complete game scope still UNVERIFIED.
- Main English table: 3572 unique IDs, 82 empty values, 241 duplicate-value groups; translated/reviewed/in-game verified: 33/0/0.
- Pilot: main-menu labels and adjacent help/navigation translated in translation/arabic/main_menu.json and merged into the ignored local bilingual master/reference. User requested this small pilot; mass translation remains gated.
- Extraction: all 8 chunk indexes parsed to EOF (90863 records); 35 localization/font-name candidates extracted, no errors. Name filtering is not proof of complete text discovery.
- Font / RTL / shaping: the user's screenshot shows Arabic main-menu labels and help with joined letters in the installed ordered build. Broader glyph/RTL/mixed-text/subtitle tests remain pending; individual records have not been promoted to in_game_verified yet.
- Repack: append-only approach failed at runtime (FileTable is out of order). Ordered rebuilding now preserves resource order and untouched stored payloads; game log passed common preloading and user screenshot confirms menu loaded.
- Installation / uninstall: locally executed install, restore and reinstall; original restoration and final installed hashes verified. Current state: INSTALLED.
- Game: Steam app 350080, build 616161, English installed.
- Source hashes: build 616161 hash pair enforced by builder/installer; only this experimental pair accepted. No public release or runtime-supported version declared.
- Current experiment: original candidate maps in all six idf+ fonts contain no Arabic-range entries. Four font/atlas pairs now have appended pilot glyphs; runtime field semantics and visual rendering still need confirmation.
- Local reference: generated 3572 records with AR above EN; source and source literals retained; repeat generation preserves existing Arabic and refuses source drift.
- Tests: 15 synthetic tests pass, including ordered middle-resource replacement, binary VTR ID boundaries and dialogue-only export; original backup/restore hash round trip completed previously.
- Git: foundation checkpoint 2d8028a pushed; tooling checkpoint recorded in Git history after this state update.
- Original backups: workspace/backups/menu_pilot_original (ignored); preserve this folder and workspace/menu_pilot for uninstall/rollback.
- Installed index SHA-256: 15c551baaa051a95a994f114a2ed1ee2061983e37edeac6ae4ebf18ec8ad4464.
- Installed resources SHA-256: 5a61ac1d59fd10d4339bca4398324c08b09a149c75d5c6c82a1aa96a19801bc9.
- Dialogue export: workspace/dialogue/ALL_DIALOGUE.local.jsonl and .md; 1586 source records, 1548 text-bearing, 15 empty, 23 placeholders. Per-source-chapter files also generated. No dialogue translated.
- Dialogue audit: 8 chunk indexes, 11533 voice resources (10538 voicetracks, 995 voiceover declarations), 999 exported IDs have direct voice-resource references, zero unresolved referenced IDs. Remaining dialogue IDs retained from source naming, not discarded.
- Limits: this exports written dialogue, not speech-to-text for audio without captions; playback order and speaker ownership inside multi-speaker blocks still need review.
- Full chunk payload audit: 90863/90863 records decoded and scanned (100%), zero failures, 50595 unique payloads; 17082 candidate source snapshots retained locally.
- Confirmed electronic-text corpus: 3574 records (3572 main English table plus 2 loose driver warnings), under workspace/all_text; primary local master and menu pilot unchanged.
- Raw supplementary candidates: 646186 quoted/UI occurrences and 190514 native-binary printable runs. These are mostly technical strings, not a claimed translation count. 204 distinct phrase candidates prepared for review.
- References: 25 missing English IDs (3 faction, 16 secrets, 6 UI), plus one preserved native key with a trailing space. No missing English fabricated.
- Current extraction percentage: archive payload scanning 100%; main English table extraction 100%; total player-visible text percentage UNKNOWN. See docs/TEXT_COVERAGE.md for explicit remaining gates.
- Tests: full suite now 19 passing synthetic tests. No new translation or game-file modifications during this audit.

## NEXT ACTION

Keep translation on HOLD. Parse/review BSWF v20 text/action fields and the 204 phrase candidates, resolve the 25 missing-source IDs based on actual use, and plan visual/native-message coverage using docs/TEXT_COVERAGE.md. Do not equate 100% payload scanning with 100% visible-text extraction; image/video/virtualtexture text and runtime-only messages remain unverified.
