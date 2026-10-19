# Contributing

Thanks for helping. Read [PROJECT_STATE.md](PROJECT_STATE.md) and
[DECISIONS.md](DECISIONS.md) before starting.

## Ground rules

- **Never commit proprietary content**: no game executables/DLLs, no `chunk0.*`,
  no `*.resources`/`*.index`/`*.bimage`/`*.bfont`/`*.bik`, no complete English
  script or extracted corpus, no backups.
- Never commit secrets, tokens, `.env` files or developer absolute paths.
- Keep native `#str_` IDs stable and preserve placeholders, timing tags and
  language tags exactly.
- Arabic source stays normal Unicode (logical order); shaping/PUA is generated at
  build time.
- Do not claim in-game verification without a real screenshot/log.

## Checks before opening a pull request

```powershell
python -m unittest discover -s tests -v
python -m pytest tests -q
python tools/check_public_repo.py
```

`check_public_repo.py` must report zero violations.

## Translation contributions

**On hold.** The license for the Arabic translation data under `translation/` is
not settled yet (see the open decision in `DECISIONS.md`). Do not submit
translation batches until it is. Once open, contributions must follow
`translation/glossary/GLOSSARY.md` and `docs/localization/TRANSLATION_GUIDE.md`.

## Bug reports

Report tooling defects with a synthetic reproduction and hashes where possible.
Never attach game files or personal paths. See [SECURITY.md](SECURITY.md) for
security issues.
