# Project state

Date: 2026-10-15

- Phase: archive discovery and local bilingual reference established; font research next.
- Build: no installable build; last successful build: none.
- Translation percentage: 0.92% of the main English table; complete game scope still UNVERIFIED.
- Main English table: 3572 unique IDs, 82 empty values, 241 duplicate-value groups; translated/reviewed/in-game verified: 33/0/0.
- Pilot: main-menu labels and adjacent help/navigation translated in translation/arabic/main_menu.json and merged into the ignored local bilingual master/reference. User requested this small pilot; mass translation remains gated.
- Extraction: all 8 chunk indexes parsed to EOF (90863 records); 35 localization/font-name candidates extracted, no errors. Name filtering is not proof of complete text discovery.
- Font / RTL / shaping: UNVERIFIED.
- Repack / installation / uninstall: not implemented or tested.
- Game: Steam app 350080, build 616161, English installed.
- Source hashes: see discovery report; no version approved for patching yet.
- Current experiment: six idf+ font resources. A candidate character map after 12-byte glyph records is sorted in all six files and contains no Arabic-range entries. Field semantics remain UNVERIFIED; no font modification or game installation performed.
- Local reference: generated 3572 records with AR above EN; source and source literals retained; repeat generation preserves existing Arabic and refuses source drift.
- Tests: 6 synthetic tests pass, including corruption rejection, sync-flush decoding and reference preservation.
- Git: foundation checkpoint 2d8028a pushed; tooling checkpoint recorded in Git history after this state update.
- Blockers: localization serialization, font format, repacking and runtime rendering remain unproven.

## NEXT ACTION

Prepare the requested main-menu runtime pilot: verify idf+ character/glyph layout and bimage encoding, generate licensed Arabic glyphs, and prove a no-op archive/index rebuild. Then test one translated menu string with actual game evidence before installing the full 33-entry pilot. Translation source is ready; no installable pilot exists yet.
