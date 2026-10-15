# Installation

An experimental 33-entry menu pilot has been installed locally on the exact source hash pair for Steam build 616161. Loader acceptance and Arabic rendering are not yet visually verified. This is not a public release.

Close the game before installation or restoration. From the repository root, after building with BUILD_GUIDE.md:

```powershell
.\INSTALL_ARABIC.ps1 -GamePath "<your Steam game directory>"
.\UNINSTALL_ARABIC.ps1 -GamePath "<your Steam game directory>"
```

Equivalent Python commands:

```powershell
python tools/install_menu_pilot.py --game "<your Steam game directory>"
python tools/install_menu_pilot.py --game "<your Steam game directory>" --uninstall
```

The installer refuses unknown current hashes or a running game, verifies generated files, creates exclusive original backups, stages both replacements and verifies installed hashes. A partial replacement failure restores the already-replaced files. Uninstall requires known patch hashes plus verified original backups and restores the original bytes.

Keep `workspace/backups/menu_pilot_original/` and `workspace/menu_pilot/`. The local install manifest records exact paths and hashes. Both directories are ignored by Git. A real install → uninstall → reinstall round trip has passed, with original and modified hashes matching their expected values.
