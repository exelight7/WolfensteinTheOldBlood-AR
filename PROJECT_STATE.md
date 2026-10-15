# Project state

Date: 2026-10-15

- Phase: archive discovery and local bilingual reference established; font research next.
- Build: no installable build; last successful build: none.
- Translation percentage: 0% of the main English table; complete game scope still UNVERIFIED.
- Main English table: 3572 unique IDs, 82 empty values, 241 duplicate-value groups; translated/reviewed/in-game verified: 0/0/0.
- Extraction: all 8 chunk indexes parsed to EOF (90863 records); 35 localization/font-name candidates extracted, no errors. Name filtering is not proof of complete text discovery.
- Font / RTL / shaping: UNVERIFIED.
- Repack / installation / uninstall: not implemented or tested.
- Game: Steam app 350080, build 616161, English installed.
- Source hashes: see discovery report; no version approved for patching yet.
- Current experiment: six font metrics resources identified with idf+ signatures; internal glyph layout not yet proven.
- Local reference: generated 3572 records with AR above EN; source and source literals retained; repeat generation preserves existing Arabic and refuses source drift.
- Tests: 6 synthetic tests pass, including corruption rejection, sync-flush decoding and reference preservation.
- Git: foundation checkpoint 2d8028a pushed; tooling checkpoint recorded in Git history after this state update.
- Blockers: localization serialization, font format, repacking and runtime rendering remain unproven.

## NEXT ACTION

Reverse engineer the six extracted idf+ font resources and their bimage atlases using independent documented evidence. Prove a no-op archive/index rebuild before a one-string pilot. Reproduce extraction and reference generation with docs/BUILD_GUIDE.md; do not mass translate or install until the rendering pilot is verified.
