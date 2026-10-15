# Installation

An experimental 33-entry menu pilot has been installed locally on the exact source hash pair for Steam build 616161. The ordered rebuild passed startup and the owner's Arabic main-menu screenshot. This is not a public release or full-game verification.

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

Keep `workspace/backups/menu_pilot_original/` and `workspace/menu_pilot_ordered/`. The local install manifest records exact paths and hashes. Both directories are ignored by Git. A real install → uninstall → reinstall round trip passed for the initial pilot; it was later restored and superseded by the ordered build after the initial build failed at runtime. Current ordered installed hashes match its manifest. The previous workspace/menu_pilot files remain only as failure evidence and are blocked from installation.
