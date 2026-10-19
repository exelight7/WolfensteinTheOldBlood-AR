# Wolfenstein: The Old Blood â€” Arabic Localization

ØªØ¹Ø±ÙŠØ¨ ØºÙŠØ± Ø±Ø³Ù…ÙŠ Ù„Ù„Ø¹Ø¨Ø© Wolfenstein: The Old Blood Ø¹Ù„Ù‰ Steam (ÙˆÙŠÙ†Ø¯ÙˆØ²).
Unofficial Arabic fan localization for the Windows Steam release.

> Status: **v1.0.0.** The confirmed electronic-text corpus is fully translated,
> verified and packaged with a Windows installer/manager. The installer rebuilds
> the localization from the user's own vanilla game files; no game assets are
> redistributed. See [PROJECT_STATE.md](PROJECT_STATE.md) for the release evidence.

## What this is

- A community Arabic (ÙØµØ­Ù‰) localization of *Wolfenstein: The Old Blood* text.
- Scope is the **confirmed electronic-text corpus of 3574 records**: 3572 entries
  of `strings/english.lang` plus 2 loose driver-warning strings. Of these,
  **3376 are translated** and **198 are intentionally left untranslated**
  (technical labels, empty/glyph metadata and placeholders) â€” every skipped record
  is recorded with an explicit reason.
- This is **not** a claim of 100% of every visible pixel of text. BSWF/menu
  textures, image textures, Bink video and native engine messages are out of scope
  and remain **UNCERTIFIED**. See [docs/discovery/TEXT_COVERAGE.md](docs/discovery/TEXT_COVERAGE.md).

Original game assets, the complete English script and the extracted corpus stay
**local only** and are excluded from Git. You need your own legally purchased copy.

## Installation

Download `WolfensteinAR-Manager-1.0.0-x64-setup.exe` from
[Releases](https://github.com/exelight7/WolfensteinTheOldBlood-AR/releases).
The desktop manager detects a supported game version, verifies the base files
against known hashes, backs up the originals, applies the patch atomically and
can restore the vanilla state at any time.

Manual build/install procedures for contributors are documented in
[docs/build/BUILD_GUIDE.md](docs/build/BUILD_GUIDE.md) and
[docs/build/INSTALL_GUIDE.md](docs/build/INSTALL_GUIDE.md). The desktop app is
documented in [app/README.md](app/README.md).

Only game versions listed in [config/supported_versions.json](config/supported_versions.json)
are accepted; unknown states are refused rather than overwritten.

## How it works

- Translations are stored as normal Unicode Arabic (logical order) with the
  original native `#str_` ID and a SHA-256 of the source English; the English text
  itself is never committed.
- At build time the text is shaped (shaping + BiDi), and Arabic glyphs are appended
  to the game fonts using an append-only SDF/PUA scheme that preserves the original
  glyph indices, kerning and atlas pixels. The typeface source is IBM Plex Sans
  Arabic (OFL) â€” see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Formatting placeholders, timing tags and language tags are preserved exactly and
  enforced by the batch validator.

## Repository layout

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md). In short:

- `app/` â€” Tauri 2 + React desktop manager and NSIS installer.
- `translation/` â€” public Arabic translation data and glossary (no English).
- `tools/` â€” extraction, build, sidecar, validation and release-safety tooling.
- `tests/` â€” synthetic-only unit tests (`python -m unittest discover -s tests -v`).
- `config/supported_versions.json` â€” the game-version gate.
- `reports/` â€” generated QA reports.
- `reference/`, `workspace/` â€” local-only masters, corpus and builds (Git-ignored).

## Development

```powershell
python -m pip install -r requirements-pilot.txt pytest pyinstaller
python -m unittest discover -s tests -v
python -m pytest tests -q
python tools/check_public_repo.py   # fails if the repo would leak secrets/assets

# Desktop app + sidecar (Windows x64)
python tools/prepare_release_data.py
python tools/build_sidecar.py
cd app
npm ci
npm run typecheck
npm run lint
npm run tauri build
```

The sidecar is a PyInstaller one-file executable bundled under the app's
resources. It reads the user's verified vanilla `chunk0`, joins the shipped Arabic
by ID while validating each source hash, and emits the patched archives plus a
hash manifest.

## Licensing

- Source code and tooling: **MIT** (see [LICENSE](LICENSE)).
- Translation data under `translation/`: shared for the community; see
  [CONTRIBUTING.md](CONTRIBUTING.md) and [DECISIONS.md](DECISIONS.md).
- The game and its assets are **not** open source and are not distributed here.
  See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
