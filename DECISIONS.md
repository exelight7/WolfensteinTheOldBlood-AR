# Decisions

## 2026-10-15 — Preserve source assets and isolate research

Use the installed game read-only. Store research dependencies, extracted resources, manifests containing local paths, and experiments under ignored `workspace/`.

Evidence: installed Steam build 616161 and chunk0 hashes recorded in discovery. No archive installation or replacement has been attempted.

## 2026-10-15 — External reference without vendoring

The inspected ID-Tech-5 commit has no license file in its tracked root. Do not redistribute its source. Implement independent tooling from documented format observations and verify against local bytes. No upstream script has been executed.

## 2026-10-15 — Rendering strategy remains open

Test native Unicode first, then pre-shaped text, then PUA/atlas approaches if necessary. No strategy is selected before an in-game pilot demonstrates its behavior.
