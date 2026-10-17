# Project structure

This document describes the repository layout, which areas are protected, and
which data is regenerable versus irreplaceable. Keep it current when the
layout changes.

## Root

The root contains only major project documents and entry points:

- `README.md` — project overview and repository pointers.
- `PROJECT_STATE.md` — authoritative state ledger (most recent overall status).
- `DECISIONS.md` — dated engineering decisions with evidence (append-only history).
- `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `LICENSE`, `THIRD_PARTY_NOTICES.md` — governance files.
- `last_reporting.md` — latest supervisor handoff report (single file, always overwritten).
- `requirements-pilot.txt` — pinned pilot Python dependencies.
- `config/supported_versions.json` — game-version gate (empty until a runtime-supported
  version is declared).
- `scripts/` — PowerShell install/uninstall entry points.

Do not leave generated artifacts, archives, fonts or extracted game data at root.

## docs

Documentation grouped by topic:

- `docs/discovery/` — reverse-engineering and extraction records:
  `DISCOVERY_REPORT.md`, `ARCHIVE_FORMAT.md`, `TEXT_COVERAGE.md`,
  `DIALOGUE_EXTRACTION.md`, `LOCALIZATION_FORMAT.md`.
- `docs/fonts/` — font findings and Arabic rendering strategy:
  `FONT_SYSTEM.md`, `ARABIC_RENDERING.md`.
- `docs/localization/` — translation procedures:
  `TRANSLATION_GUIDE.md`, `TRANSLATION_BATCHES.md`.
- `docs/build/` — build and installation procedures:
  `BUILD_GUIDE.md`, `INSTALL_GUIDE.md`.
- `docs/qa/` — quality gates: `QA_GUIDE.md`.
- `docs/distribution/` — distribution/licensing and research provenance:
  `DISTRIBUTION_STRATEGY.md`, `TOOLS.md`.
- `docs/PROJECT_STRUCTURE.md` — this file.

Cross-links between doc groups use relative paths (`../fonts/FONT_SYSTEM.md` etc.).

## tools

All active Python tools stay **flat** in `tools/` (no subfolders):

- `archive_inventory.py`, `collect_text_corpus.py`, `audit_text_sources.py`,
  `local_reference.py`, `extract_dialogue.py`, `apply_translation_batch.py`,
  `verify_translation_corpus.py`, `build_menu_pilot.py`,
  `install_menu_pilot.py`, `pilot_font.py`, `fetch_pilot_font.py`.

Reason: tests (`tests/test_*.py`) add `tools/` to `sys.path` via
`parents[1] / "tools"` and the tools import each other flat
(`from archive_inventory import records`, `from local_reference import parse_lang`,
etc.). Tests inject temporary directories for most filesystem operations, so no
tool file needs to exist anywhere else.

## scripts

`scripts/INSTALL_ARABIC.ps1` and `scripts/UNINSTALL_ARABIC.ps1` are thin wrappers
around `python tools/install_menu_pilot.py`. They resolve the repository root from
their own location (`Split-Path $PSScriptRoot -Parent`), so they may be called as
`.\scripts\INSTALL_ARABIC.ps1 -GamePath "<game directory>"` from the repository root.

## tests

Synthetic-only tests in `tests/` using the project's `unittest` suite
(`python -m unittest discover -s tests -v`, currently 25 tests). No real game
fixtures are committed; check the baseline count before/after tooling changes.

## translation (public, tracked)

- `translation/arabic/main_menu.json` — the 33-entry in-pilot menu batch.
- `translation/arabic/phase_25.json`, `phase_50.json`, `phase_75.json`,
  `phase_100.json` — staged public Arabic batches (Arabic + ID + source hash +
  status; never the proprietary English text). Do not rename IDs, rewrite Arabic,
  or alter English hashes.

## reference (local authoritative, Git-ignored)

Generated local masters — regenerate via `python tools/local_reference.py`:

- `reference/translation_master.local.jsonl` — canonical local bilingual master.
- `reference/english_source.local.lang` — preserved copy of the original table bytes.
- `reference/ALL_TRANSLATIONS.local.md`, `reference/summary.local.json`.

## reports (generated + historical)

Flat directory; filenames encode the topic (`menu_pilot_build.json`,
`dialogue_extraction.json`, `text_coverage.json`, `main_menu_qa.json`,
`translation_phase_25/50/75/100.json`, `translation_final_qa.json`,
`translation_consistency.json`). Active tools write some of these paths
directly (`translation_phase_*.json`, `translation_final_qa.json`), so reports
stayed flat instead of gaining subfolders.

## workspace — full workspace breakdown

All workspace content is Git-ignored. Most subdirectories are referenced by
active tool defaults (`workspace/all_text`, `workspace/text_audit`,
`workspace/dialogue`, `workspace/inventory`, `workspace/research`,
`workspace/translation_batches`, `workspace/menu_pilot_ordered`,
`workspace/backups/menu_pilot_original`), so they deliberately keep their
current names. Layout:

- `workspace/backups/` — BACKUP. Original game archive pair
  (`menu_pilot_original/`) plus an older master backup. **Rollback keystone.**
- `workspace/menu_pilot_ordered/` — BACKUP-adjacent BUILD. The working ordered
  pilot build; uninstallation requires its exact hashes.
- `workspace/menu_pilot/` — EXPERIMENT archived in place. The superseded
  append-only build that caused the FileTable startup crash; retained as crash
  evidence (see `workspace/experiments/FILETABLE-001/`). Never install it.
- `workspace/all_text/` — corpus (confirmed text + candidate literals; large).
- `workspace/text_audit/` — per-record extraction coverage and candidate sources.
- `workspace/dialogue/` — dialogue-only export + voice references.
- `workspace/inventory/` — archive inventory manifests and selected resource bytes.
- `workspace/translation_batches/` — translation worker inputs/outputs, one-off
  worker scripts and pre-apply backups for phases 25–100.
- `workspace/research/` — IBM Plex Sans Arabic TTF (hash-pinned) + ID-Tech-5
  reference sources (never redistribute).
- `workspace/experiments/` — experiment records (FILETABLE-001 crash logs).
- `workspace/archive/` — orphaned/duplicated local artifacts moved out of the
  way but never deleted (`english.lang` early extraction copy, `font_original.png`).

## Important Protected Paths

Never casually clean, rename or move:

- `workspace/backups/menu_pilot_original/` — ORIGINAL GAME BACKUP (rollback).
- `workspace/menu_pilot_ordered/` — installed ordered build (uninstall depends on it).
- `reference/translation_master.local.jsonl`, `workspace/all_text/` — the only
  existing copies of the translation corpus/local English masters.
- `translation/arabic/` — public translation data (Phase-100 currently uncommitted).
- `workspace/experiments/FILETABLE-001/`, `workspace/menu_pilot/` — crash evidence.
- `docs/`, `PROJECT_STATE.md`, `DECISIONS.md` — reverse-engineering record.
- `workspace/backups/main_menu_pre_translation.local.jsonl` — older master backup.

## Generated vs Irreplaceable Data

**REGENERATABLE** (from the game or tracked sources):

- `workspace/inventory/`, `workspace/text_audit/`, `workspace/dialogue/data only`,
  `workspace/research/ibm_tree.local.json`,
  `reference/ALL_TRANSLATIONS.local.md`, `reference/summary.local.json`,
  `reports/*` (validated again by tools), build outputs.

**IRREPLACEABLE / MUST BACK UP** (no public or regenerable copy exists):

- `workspace/backups/menu_pilot_original/` (requires a legally installed game only —
  but verify hashes; losing it mid-install is dangerous).
- `reference/translation_master.local.jsonl`, `reference/english_source.local.lang`,
  `workspace/all_text/ALL_CONFIRMED_TEXT.local.jsonl` (+ `.md`) — the translation
  corpus with per-record source hashes.
- `translation/arabic/phase_*.json` + `translation/arabic/main_menu.json`
  (track the uncommitted Phase-100 data in Git first).
- `workspace/translation_batches/*/pre_apply_backup/` — master backups per phase.

Rule of thumb: anything under `reference/` or `workspace/all_text/`/`translation/`
is either the only copy or the authoritative copy — never bulk-delete; consult
this document first.
