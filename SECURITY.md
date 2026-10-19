# Security

## Reporting

Report security issues privately to the maintainers (open a minimal GitHub issue
asking for a private channel, or use GitHub's private vulnerability reporting when
enabled). Do **not** post game files, credentials, tokens or personal paths in
public issues.

## Scope

This project ships original tooling and Arabic translation data. It does not
distribute game assets. Relevant security concerns include:

- installer/patch logic writing outside the game directory or overwriting unknown
  game states;
- path traversal or archive parsing bugs in the extraction/build tools;
- the update manifest accepting unsigned or hash-mismatched packages;
- accidental publication of local/private data.

## Expectations for tooling

- Read installed archives without modifying them during extraction.
- Refuse unknown game states instead of overwriting them.
- Verify SHA-256 hashes for every source, staged and installed file.
- Keep a verified backup and provide restore/rollback.
- Release artifacts must be hash-pinned and attached to a tagged GitHub Release.
