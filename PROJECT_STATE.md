# Project state

Date: 2026-10-19

## Localization

- Phase: **complete** for the confirmed electronic-text corpus of 3574 records
  (3572 `strings/english.lang` + 2 loose driver-warning strings).
- Counts: **3376 translated**, **198 `do_not_translate`** (technical labels,
  empty/glyph metadata, placeholders) â€” every exclusion carries an explicit
  reason. Master table: 3572 unique IDs, 82 empty values, 241 duplicate-value
  groups.
- The 33-entry main-menu pilot is merged into `translation/arabic/main_menu.json`.
- This is **not** a claim of 100% of all visible game text. BSWF/menu textures,
  image textures, Bink video and native engine messages remain **UNCERTIFIED**;
  see `docs/discovery/TEXT_COVERAGE.md`.

## Third review (v1.0.0 text freeze)

- Automated re-validation of all 3574 records: **0** token/placeholder errors,
  **0** master/corpus Arabic mismatches, **0** bidi/PUA artifacts. All flagged
  formatting patterns were triaged as source-faithful and intentional.
- Manual sampling of UI/achievement/challenge/dialogue records resolved the 13
  outstanding `needs_context` items (German `legen/liegen` â†’ `ÙˆØ¶Ø¹/Ø§Ø³ØªÙ„Ù‚Ù‰`) and
  corrected **20** genuine defects (Agent Two gender, passive voice, plural verb
  agreement, ghoul plural, an idiom, an elliptical clause and the controller
  rebind dialog).
- Evidence: `workspace/release_review/` (`THIRD_REVIEW.local.json`,
  `RELEASE_LANGUAGE_REPORT.local.json`, `CONTEXT_RESOLUTION.local.json`,
  `LANGUAGE_FIXES*.local.json`, and timestamped backups).

## Build

- Rebuilt the runtime from the frozen source.
  - `workspace/runtime_full/` â€” `chunk0.index`
    `5b8b17caâ€¦e2b5916`, `chunk0.resources` `35887440â€¦3e38477`.
  - `workspace/runtime_complete/` â€” `chunk0.index`
    `c29a2b83â€¦c006f61`, `chunk0.resources` `46a3dfccâ€¦23f6f60`,
    `text/english.lang` `b4fb2ddbâ€¦05068017`. Static gate **passes**.
- Exact hashes are registered in `config/supported_versions.json`.

## Installation

- The owner's machine currently runs the previous review build
  (`runtime_complete_reviewed`: `chunk0.index` `d6da4489â€¦0739126`,
  `chunk0.resources` `217e6189â€¦ec504511`). The v1.0.0 build above is **not yet
  installed locally**; the desktop installer owns that operation.
- The NSIS installer was built and silently test-installed to a temporary folder;
  the installed app launches and bundles `resources/sidecar/wtob-build.exe`.
- Rollback keystones: `workspace/backups/menu_pilot_original/` (vanilla) and
  `workspace/backups/runtime_complete_reviewed_pretest/`. `scripts/UNINSTALL_*.ps1`
  restore the vanilla state.

## Desktop app

- Tauri 2 + React manager under `app/`: Steam/manual detection, hash-based state
  classification, verified backup, transactional install/rollback, repair,
  restore, update checks and an Arabic RTL UI.
- The sidecar (`tools/release_build.py`, packaged as
  `resources/sidecar/wtob-build.exe`) rebuilds from the user's own verified vanilla
  `chunk0`, validates every shipped English hash and reproduces the exact v1
  payload hashes (`c29a2b83â€¦`, `46a3dfccâ€¦`, `d995be90â€¦`).
- Installer: `WolfensteinAR-Manager-1.0.0-x64-setup.exe`, 44,734,430 bytes
  (42.66 MiB), SHA-256
  `cfe7c3684af82c32df720acd739fb3b6d3837ddd2f9f11c322deab8716d4f71a`
  (values published on the GitHub Release; the local build differs only in
  size/hash because the CI runner rebuilds the binary).
- Update manifest: `release/release-manifest.json` (camelCase schema consumed by
  `app/src-tauri/src/manifest.rs`).

## Repository

- Open-source audit clean: no secrets, no developer absolute paths, no
  English/proprietary content. `.gitignore` hardened for Node/Rust builds, env
  files, archives, generated release data and generic `*.local.*`.
- Licensing: code MIT (`LICENSE`). Translation-data licensing is still an open
  owner decision (see `DECISIONS.md`).
- Tests: **137** Python tests plus **39** Rust tests. Frontend typecheck/lint and
  `cargo clippy --all-targets -- -D warnings` pass.

## Release gates

| Gate | Status |
| --- | --- |
| Localization review + freeze | PASS |
| Static build verification | PASS |
| Language gate | PASS |
| Public-repo gate | PASS |
| Python test suite | PASS (137) |
| Rust tests + clippy | PASS (39) |
| App typecheck + lint | PASS |
| Frontend production build | PASS |
| NSIS installer exists | PASS (42.66 MiB) |
| Packaged sidecar reproduces v1 hashes | PASS |
| Backup/restore rollback tests | PASS |
| Update manifest | PASS |
| CI + release workflows | PASS |
| GitHub tag `v1.0.0` + Release | PENDING |

## NEXT ACTION

Run the final gates from a clean worktree, commit the release, push `main`, tag
`v1.0.0`, and publish the GitHub Release with the installer,
`release-manifest.json` and `SHA256SUMS.txt`.
