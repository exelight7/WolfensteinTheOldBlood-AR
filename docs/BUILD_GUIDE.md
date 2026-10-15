# Extraction and local reference

Requires Python 3.10+; initial validation used Python 3.12. No extra Python dependencies. These commands generate research outputs, **not an installable mod**.

```powershell
python -m unittest discover -s tests -v
python tools/archive_inventory.py --game "<your Steam game directory>"
python tools/local_reference.py workspace/inventory/chunk0_022456.bin
```

The entry number above is verified for Steam build 616161 only. For another version inspect the inventory and locate `strings/english.lang` by its resource name. The reader is experimental, rejects malformed structures, and does not approve a version for patching.

Inventory manifests and selected resource bytes go to ignored workspace/inventory. Inspect extraction_error fields; any such field means that resource was not extracted successfully. No installed archive is written. Local reference generation preserves prior Arabic and refuses source changes rather than overwriting translation work.

Repeat generation is deterministic for identical source and existing translation data. It preserves original source bytes; this is not a verified no-op archive rebuild.

No build/install command exists yet. Repacking, Arabic font generation, shaping, QA and supported-version checks are gates for future implementation.
