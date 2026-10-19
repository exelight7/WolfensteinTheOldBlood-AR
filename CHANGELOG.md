# Changelog

All notable changes to this project are documented here.
This project follows [semantic versioning](https://semver.org/).

## [1.0.0] — 2026-10-19

First public release of the Arabic localization of the confirmed electronic-text
corpus, packaged with a Windows installer/manager.

### Localization

- Completed the confirmed electronic-text corpus: **3574 records** (3572
  `strings/english.lang` entries plus 2 loose driver-warning strings). **3376**
  translated, **198** intentionally excluded (`do_not_translate`) with reasons.
- Third full review pass: automated re-validation of all 3574 records
  (0 token/placeholder/bidi/PUA errors) plus sampled manual review, resolving the
  13 outstanding `needs_context` items and correcting 20 source-faithful defects
  (agent gender, passive voice, verb agreement, idiom, elliptical clauses and the
  controller rebind dialog).
- Locked terminology against `translation/glossary/GLOSSARY.md`.

### Build and packaging

- Rebuilt the runtime localization from the frozen source; static verification gate
  passes (`only_intended_changed`, `enigma_keys_present`, `image_change_region_ok`).
- Added `tools/check_public_repo.py` and a CI workflow that runs the full test
  suite and blocks accidental publication of secrets, developer paths or
  proprietary assets.
- Added the release version gate in `config/supported_versions.json`.

### Desktop app

- Added the Tauri 2 + React Windows manager: Steam/manual detection, hash-based
  state classification, verified backup, transactional install with rollback,
  repair, restore and update checks.
- Added a PyInstaller sidecar that rebuilds the localization from the user's own
  verified vanilla `chunk0` and validates every shipped English hash; no game
  assets or English source text are redistributed.
- Added the NSIS installer (`Wolfenstein AR Manager_1.0.0_x64-setup.exe`,
  45.33 MiB) and verified that it bundles `resources/sidecar/wtob-build.exe`.
- Added release CI: Windows app gates plus a tagged release workflow that builds
  the sidecar and installer, verifies the packaged sidecar, writes
  `release-manifest.json`/`SHA256SUMS.txt` and publishes the GitHub Release.
- Tests: 39 Rust tests, 130 Python tests; `cargo clippy --all-targets -D warnings`
  and the frontend typecheck/lint/build pass.

## [0.x] — 2026-10-15 — historical research milestones

- Repository foundation, archive format reverse-engineering and complete
  extraction of 90863 chunk payloads (zero decode failures).
- Confirmed electronic-text corpus of 3574 records and protected local bilingual
  reference generation.
- Experimental main-menu pilot with IBM Arabic PUA/SDF glyphs, installed and
  restored with verified hashes.
- Staged translation phases 25/50/75/100 with immutable-source, token and
  placeholder validation.
