# Translation stages

Owner authorized percentage stages: 25%, 50%, 75%, 100%, based on the current confirmed corpus of 3574 records. Checkpoints are 894, 1787, 2681 and 3574 processed records. Existing 33 menu translations count toward the first checkpoint.

Completion means processed records, including documented technical/empty exclusions. Reports separately expose actual translated percentages; excluded entries must never be presented as Arabic translations. Source-data completion is not linguistic review, in-game verification, or proof of complete visible-game text extraction.

New public data is split into translation/arabic/phase_25.json, phase_50.json, phase_75.json and phase_100.json; original menu data remains separate. Public records contain Arabic, stable IDs, source hashes/status/short notes, never the complete proprietary English source. Every source ID belongs to exactly one public batch.

Local inputs/outputs and backups are under ignored workspace/translation_batches. Each parallel translation worker has an exclusive phase/part directory. Only the main session merges into the canonical master/public data. Logical Arabic is required; shaping, BiDi and PUA are build output only.

```powershell
python tools/apply_translation_batch.py workspace/translation_batches/phase25/part1/output.local.jsonl workspace/translation_batches/phase25/part2/output.local.jsonl workspace/translation_batches/phase25/part3/output.local.jsonl --phase 25
# Add --apply only after the dry validation succeeds.
```

Validator rejects source changes, duplicate/unknown IDs, missing Arabic, altered token multisets, reordered square-bracket timing/language markers, changed newline counts, runtime Arabic forms/PUA and BiDi override/isolate controls. do_not_translate requires blank Arabic and an exclusion note. Existing translations cannot be silently overwritten with conflicting Arabic.

Applying writes public Arabic-only batch data, backs up local masters, updates the primary/extended corpus and regenerates Arabic-first English-below references. No installed game files are touched. Reports preserve translated, excluded, reviewed and runtime-verification distinctions.
