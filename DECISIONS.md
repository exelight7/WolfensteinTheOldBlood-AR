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

## 2026-10-15 — User-requested main-menu translation pilot

Translate 33 main-menu and adjacent help/navigation entries as a small source-data pilot, while keeping mass translation gated. Use normal Unicode Arabic, source-qualified native IDs and existing English hashes. The selected strings contain no formatting placeholders or newlines. Preserve all English and unrelated records; backup local master before merge. Status is translated, never reviewed or in_game_verified. No archive installation is implied by this translation checkpoint.

## 2026-10-15 — Install the user-requested experimental pilot

User explicitly requested installation. Generate pre-shaped/BiDi text and append PUA glyphs to four English fonts, preserving original glyph indices, kerning bytes and atlas pixels. This is a rendering hypothesis for the first runtime test, not a final engine capability conclusion. Obtain IBM font from a pinned official revision with OFL. Avoid unsupported mipmapped cyrillic and Japanese resources.

Append replacement resources locally instead of moving original archive content. Modify only selected index offset/size fields. Structural no-op, repeat-build, already-patched idempotency, 11 synthetic tests and real original restoration checks passed. Install from verified backups and hashes; current state is reinstalled pilot. In-game verification remains pending.

## 2026-10-15 — Supersede append-only repacking after runtime crash

The game reported `idBackgroundLoader::BeginBackgroundLoads: FileTable is out of order`. Restore verified originals first, then rebuild resources in the original table order and shift later offsets. Keep untouched stored payloads byte-identical. Add a regression test replacing a middle resource, and reject unordered/overlapping input. Supersedes the preceding append-to-end decision. Ordered build passed common preloading; user supplied an actual Arabic main-menu screenshot. Preserve failed build/log evidence locally.

## 2026-10-15 — Extract dialogue only

User requested all dialogue, without translation. Export source-name-classified VO, EV, actor/AI dialogue and cutscene speech; exclude menus, confirmation dialogs, speaker-name labels and title cards. Cross-reference every voiceover/voicetrack resource in the eight chunks. Binary VTR identifiers use their preceding little-endian string length to avoid treating following binary bytes as ID suffixes. Keep duplicates, timing/language tags, source literals/hashes and empty/placeholder records; don't invent speech for uncaptioned audio. Full English remains local and ignored by Git.

## 2026-10-15 — Gate translation on honest source completeness

Owner requires extraction completeness before translation. Audit all 90863 chunk payloads rather than only localization-name matches; decoding and payload scanning achieved 100% with zero failures. Keep separate metrics for known table extraction, resource coverage, confirmed text and unclassified literals. Preserve original master/IDs; generate an extended local corpus for the two loose warning strings. Retain unknown keys as English=null and keep whitespace-bearing native keys intact. Do not claim a global percentage while BSWF field coverage, missing references, image/video text and runtime messages remain unverified. Translation remains HOLD.

## 2026-10-15 — Owner authorizes staged translation

Owner clarified that 25/50/75/100 means percentage stages, authorizing translation despite remaining extraction uncertainty. Fix the progress denominator at 3574 confirmed records. Report processed and actually translated counts separately; document excluded empty/technical entries as do_not_translate with blank Arabic and explicit reasons. Preserve existing 33 menu translations, merge new source data only after automated immutable-source, token, timing and newline checks. Source Arabic stays logical Unicode. Current runtime pilot is unchanged. The main local bilingual reference is regenerated at each stage; complete English remains local.
