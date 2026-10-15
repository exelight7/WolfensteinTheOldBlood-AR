# Arabic rendering

Status: runtime rendering UNVERIFIED. A locally installed menu pilot uses generated pre-shaped/BiDi Arabic mapped to 73 appended PUA glyphs in four fonts. No actual game screenshot of the modified result has been captured yet.

Test native Unicode/shaping first. If unsupported, test generated presentation forms and BiDi, then an automatically generated PUA/bitmap mapping. Preserve logical Arabic as source. Font target: IBM Plex Sans Arabic from IBM; license acquisition and reserved-name review pending.

Pilot order: one menu string; 5–10 varied UI strings; short subtitle; complete Arabic alphabet/forms; one chapter. Capture actual game evidence before expanding.

Fixtures must cover Arabic-only text, Latin key E, number 25, parentheses, colon, question mark, controller placeholders, multiple lines and long subtitles. Verify dots, hamza, joining, baseline, clipping and alignment at every font size used.
