# Roadmap

## Done

1. Repository foundation and source inventory.
2. Verified archive reader and complete localization extraction.
3. Stable source IDs, source hashes, public Arabic database, local bilingual
   reference and placeholder QA.
4. Font serialization and licensed IBM Plex Sans Arabic source.
5. Rebuild proven in-game; Arabic main-menu rendering confirmed.
6. Arabic shaping, RTL, mixed Latin, numbers, icons and wrapping tested across
   the confirmed corpus.
7. UI/subtitle pilot reviewed and the full confirmed corpus translated in
   resumable batches (25/50/75/100).
8. Third full review pass, context resolution and text freeze for v1.0.0.
9. Desktop installer/manager application (Tauri 2 + React): game detection,
   hash-verified install, backup/restore, diagnostics, updates.
10. Reproducible Windows installer (unsigned; no code-signing certificate) and
    the CI release pipeline.
11. Packaged-app verification: silent install, bundled-sidecar check, launch
    smoke test and sidecar hash reproduction.

## Remaining for v1.0.0

12. Tag `v1.0.0` and publish the GitHub Release with the release manifest.
13. Optional: verify the packaged installer on the owner's desktop with the live
    game and record the result; reinstall the v1.0.0 payload through the app.

## After v1.0.0

- Broaden coverage beyond the confirmed electronic-text corpus (images/video/native
  engine messages) as separate, explicitly labelled efforts.
- Register additional supported game builds after verification.
- Settle the translation-data license and open community contributions.
