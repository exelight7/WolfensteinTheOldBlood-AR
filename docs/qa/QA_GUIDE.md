# QA gates

Synthetic automated checks currently cover index boundaries/truncation, complete and sync-flushed DEFLATE, rejected trailing/truncated streams, table syntax/duplicate IDs, reference determinism, original-byte retention and translation preservation/source-drift rejection.

Pending: placeholder multiset validation from measured syntax; source-version gates; font/atlas round trips; no-op archive rebuild; changed-resource-only checks; install/uninstall restoration; mixed RTL visual tests; subtitle timing and full playthrough.

In-game evidence must record source/output hashes, exact command, modified resources, scene/menu, expected and actual result, screenshot and remaining issues. No automated data check grants in_game_verified status.
