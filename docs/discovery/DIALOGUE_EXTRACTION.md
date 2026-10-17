# Local dialogue-only extraction

```powershell
python tools/extract_dialogue.py --game "<your Steam game directory>"
```

Requires the local bilingual master and original chunk0 backups. Other chunks are read directly from the installation. This is read-only for all game files, including while the menu pilot is installed.

Outputs under ignored workspace/dialogue:

- ALL_DIALOGUE.local.jsonl: source-qualified stable IDs, English, escaped source literal, English hash, blank Arabic, source index, category, chapter-code hint and voice references.
- ALL_DIALOGUE.local.md: Arabic first (blank), English immediately below; readable complete export.
- c01–c08, c15 and unassigned .local.jsonl groups: source naming groups, not guaranteed playback order. c15 is retained as the original identifier, not asserted to be a playable chapter.
- voice_references.local.json and summary.local.json: audit metadata.

Measured: 1586 selected records, 1548 with text, 15 empty, 23 placeholder strings. Categories: 884 VO/story, 344 ambient, 348 combat/AI, 10 cutscene (including an empty record). A record can contain multiple speakers, timed blocks and sentences, so this is not a spoken-line count.

Scanned 11533 voiceover/voicetrack resource occurrences across all 8 chunks. 999 selected IDs have direct references; other dialogue IDs remain because of source naming. All referenced localization IDs resolve in the master after excluding binary-adjacent false suffixes using VTR length prefixes. #str_empty and speaker-name labels are not treated as dialogue.

All original tags and embedded timestamps are retained; no segmentation, translation, deduplication or text normalization is applied. This exports written dialogue available in the English table, not a transcription of audio without captions. It does not establish that every extracted string is used in the final game's playback.

Full English outputs stay local. Only tooling, synthetic tests and aggregate statistics are committed publicly.
