# Decisions

## 2026-10-15 — Preserve source assets and isolate research

Use the installed game read-only. Store research dependencies, extracted resources, manifests containing local paths, and experiments under ignored `workspace/`.

Evidence: installed Steam build 616161 and chunk0 hashes recorded in discovery. No archive installation or replacement has been attempted.

## 2026-10-15 — External reference without vendoring

The inspected ID-Tech-5 commit has no license file in its tracked root. Do not redistribute its source. Implement independent tooling from documented format observations and verify against local bytes. No upstream script has been executed.

## 2026-10-15 — Rendering strategy remains open

Test native Unicode first, then pre-shaped text, then PUA/atlas approaches if necessary. No strategy is selected before an in-game pilot demonstrates its behavior.

## 2026-10-15 — Preserve native IDs and exact local source

Use `strings/english.lang:<native #str_ key>` as the stable resource-qualified ID. Keep original bytes, escaped source literal and decoded English locally. Source SHA-256 uses decoded UTF-8 English without normalization. Regeneration preserves Arabic/status/context and extra translator metadata; changed ID sets or English require explicit migration. Evidence: 3572 unique native keys and synthetic regeneration tests.

## 2026-10-15 — Accept documented sync-flush payloads

The initial strict DEFLATE-final-block assumption failed against local fonts. Require the observed sync-flush suffix, add an empty final block in memory, and retain exact-size and leftover-data rejection. Synthetic terminated/sync-flushed/truncated cases pass; all 35 selected game resources decode. No conclusion about rebuilding or runtime compatibility follows from extraction.
