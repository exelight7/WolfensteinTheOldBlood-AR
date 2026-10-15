# Local bilingual reference

Generated files (ignored): `ALL_TRANSLATIONS.local.md`, `translation_master.local.jsonl`, `english_source.local.lang` and `summary.local.json`.

Retain English from the user's own installation, including exact original file bytes and escaped literals. Display Arabic first, English immediately below, with stable resource-qualified native ID, resource/index, status and context. Do not publish the complete English corpus. See docs/BUILD_GUIDE.md for generation. Edit Arabic in the local JSONL master; regeneration preserves Arabic, status, context and extra translator metadata. Source/ID changes fail before output writes and require explicit migration. Back up the local master before any manual edits.
