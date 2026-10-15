# Wolfenstein: The Old Blood — Arabic Localization

Unofficial Arabic fan localization for the Windows Steam release. An **experimental main-menu pilot** can be built locally for the exact inventoried Steam version. This is not a complete localization or a verified public release.

Translation progress: 33/3,572 main English table entries translated (0.92%), covering a small main-menu pilot. Other text sources are still under investigation. No Arabic text, font, shaping, or RTL behavior has been verified in-game.

The intended typeface is IBM Plex Sans Arabic. Human translations will remain normal Unicode Arabic; any shaping or game-specific encoding will be generated during builds.

Start with [PROJECT_STATE.md](PROJECT_STATE.md), [discovery](docs/DISCOVERY_REPORT.md), and [roadmap](ROADMAP.md).

Read-only extraction and local reference commands are in [the build guide](docs/BUILD_GUIDE.md). Run `python -m unittest discover -s tests -v` for synthetic tooling checks.

The menu pilot has been installed locally and restored/reinstalled with verified hashes. Actual game rendering is still unverified. See [installation and restoration](docs/INSTALL_GUIDE.md); keep the generated build and original backup folders for uninstall.

Original game assets and the complete English script remain local and are excluded from Git. A legally installed copy is required. Our code is MIT licensed; proprietary game content is not covered by that license. Arabic translation data licensing will be established before public translation contributions.
