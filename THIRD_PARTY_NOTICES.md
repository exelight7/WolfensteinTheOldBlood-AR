# Third-party notices

- Wolfenstein: The Old Blood and its assets belong to their respective rights holders, including MachineGames and Bethesda. They are not open source and are not distributed here.
- ID-Tech-5: external research reference only, not redistributed; see docs/TOOLS.md.
- IBM Plex Sans Arabic: planned font source, not bundled yet. Official https://github.com/IBM/plex LICENSE.txt was retrieved on 2026-10-15 and preserved verbatim at licenses/IBM_Plex_OFL.txt. It identifies the Reserved Font Name "Plex". Inspect the font-specific license at the pinned font revision before distribution; use a neutral derivative name if required.
- Thai localization: public documentation only; no files, translations, fonts or mod assets used.
- Pilot IBM font source: https://github.com/IBM/plex/tree/39276912b05f700ee1dd491950c35d8697214208/packages/plex-sans-arabic. Unmodified TTF stays local; generated Arabic atlas glyphs derive from this OFL font. Any distributed derivative font resources must retain OFL/attribution and use a project-specific name, not the reserved name Plex. Original game atlas pixels are never distributed.
- Pilot Python dependencies: Pillow, NumPy, SciPy, arabic-reshaper, python-bidi and fontTools; versions are pinned in requirements-pilot.txt. Dependencies are installed externally, not vendored. Preserve their own upstream licenses if packaging them in a future release.
