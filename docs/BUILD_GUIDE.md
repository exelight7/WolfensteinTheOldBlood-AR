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

## Experimental menu pilot

Python 3.11+ is required for the installer. Install pinned pilot dependencies from requirements-pilot.txt, then fetch the official IBM font and its license:

```powershell
python -m pip install -r requirements-pilot.txt
python tools/fetch_pilot_font.py
python tools/build_menu_pilot.py --game "<your Steam game directory>" --font workspace/research/IBMPlexSansArabic-Regular.ttf
```

The builder requires original chunk0 hashes and refuses already-modified game files. If rebuilding after installation, restore originals first. It generates workspace/menu_pilot, with local archives, runtime language data and a manifest. All proprietary and generated archive data stays ignored.

The pilot pre-shapes Arabic, applies BiDi and maps 73 required shapes/punctuation glyphs to appended PUA entries. It expands four original font atlases using IBM Arabic SDF glyphs; original glyphs, codepoint indices, kerning tables and atlas pixel regions remain unchanged. It replaces nine resource records (four font/atlas pairs plus the English table), appends payloads with 16-byte alignment, and changes only the corresponding index offset/size fields.

The builder checks byte-identical no-op output, deterministic output from originals and idempotent output when applied to its already-patched pair. These are structural checks, not an in-game result. Runtime font/RTL behavior remains experimental. See INSTALL_GUIDE.md for local install and restoration.
