# Text extraction coverage — 2026-10-15

Translation gate: **HOLD**, as requested by the owner. Archive payload coverage is 100%; total game-visible text completion is **UNVERIFIED**, with no invented overall percentage.

## Measured coverage

| Scope | Result |
| --- | --- |
| Chunk indexes | 8/8 parsed to EOF |
| Indexed payloads | 90863/90863 decoded and scanned, 100%, zero failures |
| Distinct decoded payloads | 50595 |
| Preserved text/binary-UI candidate source files | 17082 |
| Main English table | 3572/3572 records extracted, 100% |
| Loose English graphics-driver warnings | 2/2 extracted |
| Confirmed electronic-text corpus | 3574 records |
| Dialogue subset | 1586 records, including 1548 with text |
| Quoted/binary-UI candidate occurrences | 646186, mostly technical identifiers, paths and authoring strings; NOT 646186 translatable game strings |
| Native executable/DLL printable candidates | 190514, NOT confirmed player-visible strings |
| Distinct additional phrase candidates after conservative filtering | 204; filtering is for review convenience, not proof of completeness |

The full English script, raw literal candidates, source resources and executable-derived text remain local under ignored workspace folders. Public reports contain aggregate counts and technical metadata only.

## Missing-reference investigation

Raw scanning found 26 IDs absent as exact English keys. One resolves to an existing key with a trailing space: `#str_vo_bj_dlc1_c03_072 `; preserve its native ID and source text, do not silently rename it. The remaining 25 absent keys occur in faction declarations (3), a general secrets declaration (16), and compiled UI (6). Missing keys are retained as blocked records with English=null, not fabricated text. Possible inherited/dead content is an inference, not a verified exclusion.

All six installed language tables were inspected: English/French/Italian/Polish/Spanish have 3572 entries; Russian has 3573, including its font alias. Differences in font alias configuration must not become accidental English dialogue entries.

## Additional-source investigation

The loose graphicsdriverwarningloc.json contains two English warning strings, now included in ALL_CONFIRMED_TEXT.local.jsonl and .md. Primary master and its IDs are unchanged.

Compiled BSWF files contain literal UI/default strings in addition to #str_ references. Some visibly concern older-game placeholders (including RAGE), dummy Lorem Ipsum, generic authoring labels or debug text. They must not all be promoted to production translation. Other labels/messages need source-field and runtime-use verification.

The related-engine source https://github.com/id-Software/DOOM-3-BFG/blob/master/neo/swf/SWF_Load.cpp is a research lead only (binary version 16 there versus local BSWF version 20). No code was copied. Current BSWF extraction conservatively collects bounded length-prefixed UTF-8 strings; it is not a complete typed BSWF parser. Original FWS HTML EditText candidates are also preserved. Text encoded as static glyph geometry or ActionScript-computed values is not proven complete by these scans.

Native .exe/.dll ASCII and ASCII-range UTF-16 runs are preserved as unclassified candidates with offsets and source hashes. They contain large amounts of code/symbol noise; no assertion is made that they reconstruct every runtime message.

## Remaining gates before claiming total completion

1. Classify additional UI literals and parse BSWF v20 text/action fields completely, separating placeholders/debug content from actual displayed text.
2. Resolve or document the 25 absent English references based on actual use, without inventing source English.
3. Review visual text in image/virtualtexture assets and 19 installed Bink videos; raw resource scans cannot read image pixels or compressed video frames. There are also 17 loose virtualtexture .pages files. No image/video OCR or full visual playthrough has occurred.
4. Review native runtime messages and computed UI labels, then validate source coverage during a full game/UI walkthrough.

These limits prevent a truthful claim that 100% of all player-visible text has been extracted. They do not negate the verified 100% decode/scan coverage of the indexed chunk payloads.

## Reproduction and local outputs

```powershell
python tools/audit_text_sources.py --game "<your Steam game directory>"
python tools/collect_text_corpus.py --game "<your Steam game directory>"
```

Use original chunk0 backups while the Arabic pilot is installed. Other chunks are read from the game; no installed file is modified by either tool.

workspace/text_audit holds complete per-record coverage, candidate source bytes, references and decode-failure evidence. workspace/all_text holds ALL_CONFIRMED_TEXT.local.jsonl/.md, LITERAL_CANDIDATES.local.jsonl, NATIVE_CANDIDATES.local.jsonl, PHRASE_REVIEW.local.jsonl and UNRESOLVED_IDS.local.jsonl. All English and proprietary source bytes remain ignored by Git.
