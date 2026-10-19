# Release assets

This directory holds the schema/template and the checked-in v1.0.0 update
manifest. CI regenerates the manifest for future releases and attaches it to the
GitHub Release; do not hand-edit the published asset.

## Assets attached to a release

| Asset | Purpose |
| --- | --- |
| `Wolfenstein AR Manager_<version>_x64-setup.exe` | Windows NSIS installer/manager. |
| `release-manifest.json` | Version, minimum app version, supported game build, file sizes and SHA-256 hashes. |
| `SHA256SUMS.txt` | Human-readable checksums. |

The installer bundles the localization sidecar and public Arabic data. It never
contains game archives, game executables, English source text or the font binary.

## Manifest rules

- `version` — semver of the localization/app release.
- `channel` — currently only `stable`.
- `minimumAppVersion` — oldest app that may install this package.
- `gameVersion` — game build string (`616161` for Steam app 350080).
- `files` — every asset needs `name`, `size`, `sha256` and an HTTPS
  `downloadUrl` under this repository's Releases.
- The app verifies the manifest version, semver shape, HTTPS URLs, file names and
  every payload hash before installing.
- No absolute paths, usernames, tokens or game assets appear in any asset.

See `release-manifest.template.json` for the exact camelCase shape expected by
`app/src-tauri/src/manifest.rs`.
