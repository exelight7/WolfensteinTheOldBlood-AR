# Project state

Date: 2026-10-24

## Release 1.0.1

- Owner authorized stable publication with desktop and manual downloads.
- Arabic README redesigned with an original red/black SVG banner and clear download choices.
- Release title and concise notes are Arabic (`release/RELEASE_NOTES_AR.md`).
- Windows desktop manager: Tauri 2 + React; Steam/manual detection, verified
  backup, staged install/rollback, repair, restore and update checks.
- Manual ZIP: Install.cmd / Restore.cmd, Arabic PowerShell guidance, frozen
  builder and licenses. No Python installation or game archives are required
  in the download. Builds from the user's supported originals locally.
- Publication is performed by the v1.0.1 tag workflow; the published manifest
  is authoritative for downloadable artifact sizes and hashes.

## Localization and font repair

- Confirmed corpus: 3574 records, 3376 translated, 198 intentional exclusions.
  Translation phases 25/50/75/100 are complete. Logical Arabic remains canonical.
- Added Enigma labels and the photosensitivity warning image in the final build.
- The font generator previously left 47 Arabic glyphs in each of four fonts
  with a -1 kerning-start link despite 2162 pair adjustments. All 3358 original
  glyphs across six fonts establish the correct first-row / -1 relationship.
- Repaired 188 links. Native glyphs, atlas images, text, advances and pair values
  are preserved. The independent verifier now checks links and the diagnostic
  follows them instead of bypassing missing links with a whole-table lookup.
- Corrected full payload hashes are in config/supported_versions.json:
  chunk0.index c29a2b83…c006f61; chunk0.resources f14edf90…76bb061.
- Owner's live installation is the earlier reviewed translation with only the
  font links repaired: index d6da4489…0739126; resources 14f1a1cd…eb00155.
  Verified pre-fix backup: workspace/backups/font_joining_pretest/.
- Vanilla backup workspace/backups/menu_pilot_original/ now has all three exact
  original files, including the driver warning JSON verified against its hash.

## Verification

- 143 Python tests and 39 Rust tests pass. Frontend typecheck/lint/build and
  cargo clippy pass. Public-repository guard reports zero violations.
- Frozen builder generated the manual payload with the expected full hashes.
- Manual install and restore on an isolated copy of the supported vanilla
  files succeeded; all three restored hashes matched exactly.
- Unknown-state refusal was tested: installation failed without changing files.
- NSIS installer was silently installed to an isolated directory; bundled
  sidecar/OFL/dependency notices and packaged-app launch were verified.
- Earlier Arabic main-menu rendering was confirmed by the owner. Visual
  confirmation of this font-link repair and a full playthrough remain pending.
  Do not describe static verification as a real game screenshot.

## Scope and remaining work

- Corpus completion is 100%; coverage of every image/video/native message is
  not certified. See docs/discovery/TEXT_COVERAGE.md.
- Translation-data licensing is still an owner decision; code is MIT and the
  IBM font is OFL. Both downloadable packages include license notices.
- Additional stores/builds need separate verification. The installer is unsigned.
- Historical pilot scripts remain research tools; current installation guidance
  is docs/build/INSTALL_GUIDE.md. Do not publish proprietary local references,
  extracted assets, backups or generated game archives.
