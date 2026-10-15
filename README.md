# Wolfenstein: The Old Blood — Arabic Localization

Unofficial Arabic fan localization for the Windows Steam release. An **experimental main-menu pilot** can be built locally for the exact inventoried Steam version. This is not a complete localization or a verified public release.

Translation stage25: 894/3574 confirmed records processed (25.01%): 799 translated and 95 excluded as technical/empty metadata. The owner supplied an actual screenshot showing the small Arabic main-menu pilot; new translation batches are source data and have not been installed. Subtitle rendering, broader mixed RTL cases and full-game compatibility remain unverified.

The intended typeface is IBM Plex Sans Arabic. Human translations will remain normal Unicode Arabic; any shaping or game-specific encoding will be generated during builds.

Start with [PROJECT_STATE.md](PROJECT_STATE.md), [discovery](docs/DISCOVERY_REPORT.md), and [roadmap](ROADMAP.md).

Read-only extraction and local reference commands are in [the build guide](docs/BUILD_GUIDE.md). Run `python -m unittest discover -s tests -v` for synthetic tooling checks.

The ordered menu pilot has been installed locally with verified hashes; startup and main-menu display have been confirmed. See [installation and restoration](docs/INSTALL_GUIDE.md); keep the generated build and original backup folders for uninstall.

Dialogue-only export is available locally: 1586 source records, 1548 with text; no dialogue translation performed. See [extraction instructions](docs/DIALOGUE_EXTRACTION.md). Full English is excluded from Git.

Text audit: 100% of 90863 chunk payloads decoded/scanned; 3574 confirmed electronic-text records extracted. This is **not** a claim of 100% of all visible game text. The owner authorized staged translation of this confirmed corpus; remaining [coverage gates](docs/TEXT_COVERAGE.md) are tracked separately.

Original game assets and the complete English script remain local and are excluded from Git. A legally installed copy is required. Our code is MIT licensed; proprietary game content is not covered by that license. Arabic translation data licensing will be established before public translation contributions.
