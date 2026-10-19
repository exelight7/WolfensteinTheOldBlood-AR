# Third-party notices

- Wolfenstein: The Old Blood and its assets belong to their respective rights
  holders, including MachineGames and Bethesda. They are not open source and are
  not distributed here.
- ID-Tech-5: external research reference only, not redistributed; see
  `docs/distribution/TOOLS.md`.
- IBM Plex Sans Arabic: the typeface source used to derive the appended Arabic
  glyphs. Licensed under the SIL Open Font License; the license text is preserved
  verbatim at `licenses/IBM_Plex_OFL.txt` and identifies the Reserved Font Name
  "Plex". Any distributed derivative font resources must retain the OFL and
  attribution and must not use the reserved name "Plex". The unmodified TTF stays
  local; original game atlas pixels are never distributed.
- Thai localization: public documentation only; no files, translations, fonts or
  mod assets used.

## Application stack (v1.0.0 desktop installer/manager)

The desktop application is built with the following open-source projects. Their
licenses are compatible with the MIT-licensed application; exact versions are
pinned in the application's lockfiles and summarized in the generated
`NOTICE`/SBOM artifact attached to each release.

- Tauri (Rust) and its plugins — Apache-2.0 / MIT.
- React, React DOM, TypeScript, Vite and Tailwind CSS — MIT.
- Rust crates used by the Tauri backend — per-crate licenses (MIT/Apache-2.0);
  the release SBOM records the resolved set.
- Python tooling dependencies (Pillow, NumPy, SciPy, arabic-reshaper,
  python-bidi, fontTools) are used to build the localization sidecar; versions
  are pinned in `requirements-pilot.txt` and are not vendored. Preserve their
  upstream licenses if the sidecar is bundled in a release.

## Game-content disclaimer

The MIT license covers only this project's original code and data. It does not
grant any rights to Wolfenstein: The Old Blood, its assets, or the IBM typeface.
Users must own a legitimate copy of the game.
