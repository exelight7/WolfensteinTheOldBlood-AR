# Project state

Date: 2026-10-15

- Phase: experimental main-menu patch built and installed locally; actual game rendering pending.
- Build: workspace/menu_pilot, 33 translated records, 73 generated Arabic forms mapped to PUA, four font/atlas pairs changed. Last successful build: menu pilot on 2026-10-15.
- Translation percentage: 0.92% of the main English table; complete game scope still UNVERIFIED.
- Main English table: 3572 unique IDs, 82 empty values, 241 duplicate-value groups; translated/reviewed/in-game verified: 33/0/0.
- Pilot: main-menu labels and adjacent help/navigation translated in translation/arabic/main_menu.json and merged into the ignored local bilingual master/reference. User requested this small pilot; mass translation remains gated.
- Extraction: all 8 chunk indexes parsed to EOF (90863 records); 35 localization/font-name candidates extracted, no errors. Name filtering is not proof of complete text discovery.
- Font / RTL / shaping: IBM Plex Arabic SDF glyphs generated; reshaping/BiDi/PUA used experimentally. Actual renderer behavior remains UNVERIFIED.
- Repack: append-only rebuilt pair passes byte-identical no-op, deterministic rebuild and already-patched idempotency checks. Runtime archive compatibility UNVERIFIED.
- Installation / uninstall: locally executed install, restore and reinstall; original restoration and final installed hashes verified. Current state: INSTALLED.
- Game: Steam app 350080, build 616161, English installed.
- Source hashes: build 616161 hash pair enforced by builder/installer; only this experimental pair accepted. No public release or runtime-supported version declared.
- Current experiment: original candidate maps in all six idf+ fonts contain no Arabic-range entries. Four font/atlas pairs now have appended pilot glyphs; runtime field semantics and visual rendering still need confirmation.
- Local reference: generated 3572 records with AR above EN; source and source literals retained; repeat generation preserves existing Arabic and refuses source drift.
- Tests: 11 synthetic tests pass, including partial installation rollback, real local backup/restore hash round trip also completed.
- Git: foundation checkpoint 2d8028a pushed; tooling checkpoint recorded in Git history after this state update.
- Original backups: workspace/backups/menu_pilot_original (ignored); preserve this folder and workspace/menu_pilot for uninstall/rollback.
- Installed index SHA-256: fba085198863672fdc7ce8fa04b41be5985c839afc0b46496440b4e1114a26cf.
- Installed resources SHA-256: 15d58cdf7a2353d5e48c25aee94824ffca51423a1013932698d29013899f24fd.
- Blocker: actual game screenshot is needed to verify loader acceptance, glyph appearance, joining, direction, clipping and spacing. No in-game success claimed.

## NEXT ACTION

Open the installed Steam game and capture the main menu. Confirm NEW/CHAPTERS/OPTIONS/CHALLENGES/EXTRAS/EXIT labels and help text now use Arabic, then inspect joining, direction and clipping. If loader/font rendering fails, preserve evidence and use UNINSTALL_ARABIC.ps1 to restore verified originals before changing the next experimental variable. Do not mass translate yet.
