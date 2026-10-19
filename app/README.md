# Wolfenstein AR Manager

Windows desktop manager for the Arabic localization. Built with Tauri 2, React
and TypeScript. It never writes to a game it does not recognize and always
creates or reuses a verified vanilla backup before installing.

## Features

- Steam detection (registry + `libraryfolders.vdf`) and manual folder selection.
- SHA-256 classification into supported, installed, update-available, broken and
  unknown states.
- Verified backup, transactional install with rollback, repair and restore.
- Update check against the release manifest on GitHub.
- Arabic RTL UI; all game text is built locally by the bundled sidecar.

## Requirements

- Windows 10/11 x64, WebView2, Node 24, Rust stable MSVC, Python 3.12 with
  `requirements-pilot.txt`, and PyInstaller.

## Build

From the repository root:

```powershell
python tools/prepare_release_data.py
python tools/build_sidecar.py
cd app
npm ci
npm run typecheck
npm run lint
npm run tauri build
```

The installer is written to
`app/src-tauri/target/release/bundle/nsis/WolfensteinAR-Manager-1.0.0-x64-setup.exe`.

`prepare_release_data.py` copies the public translation partitions and the
hash-pinned IBM Plex Sans Arabic font, and converts `config/pua_mapping.json` into
the internal build-info file. `build_sidecar.py` produces the one-file sidecar at
`src-tauri/resources/sidecar/wtob-build.exe`. Both generated paths are ignored by
Git and rebuilt in CI.

## Data and safety

- The installer contains no game archives, executable, English source text or
  font binary.
- The backend resolves payloads from the user's own vanilla archives (or the
  app's verified backup) and validates the sidecar's output hashes before use.
- A backup is always required before a non-vanilla install; restore refuses
  unknown states.
- State and backups live under `%LOCALAPPDATA%\WolfensteinAR\`.

## Tests

```powershell
cd app
npm run typecheck
npm run lint
cd src-tauri
cargo test
cargo clippy --all-targets -- -D warnings
```
