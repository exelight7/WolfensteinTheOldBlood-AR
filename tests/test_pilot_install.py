from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.install_menu_pilot import replace_pair, digest


class InstallTests(unittest.TestCase):
    def fixture(self, root):
        sources, targets, backups = {}, {}, {}
        for name in ("chunk0.index", "chunk0.resources"):
            sources[name], targets[name], backups[name] = (root / (name + suffix) for suffix in (".new", ".target", ".backup"))
            sources[name].write_bytes(b"new " + name.encode())
            targets[name].write_bytes(b"original " + name.encode())
            backups[name].write_bytes(targets[name].read_bytes())
        return sources, targets, backups

    def test_install_restore_and_failed_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            sources, targets, backups = self.fixture(Path(temp))
            expected = {n: digest(p) for n, p in sources.items()}
            originals = {n: digest(p) for n, p in backups.items()}
            with self.assertRaises(ValueError):
                replace_pair(sources, targets, {n: "wrong" for n in sources}, backups)
            self.assertEqual({n: digest(p) for n, p in targets.items()}, originals)
            replace_pair(sources, targets, expected, backups)
            self.assertEqual({n: digest(p) for n, p in targets.items()}, expected)
            replace_pair(backups, targets, originals, sources)
            self.assertEqual({n: digest(p) for n, p in targets.items()}, originals)

    def test_partial_replace_rolls_back(self):
        import os
        real_replace = os.replace
        with tempfile.TemporaryDirectory() as temp:
            sources, targets, backups = self.fixture(Path(temp))
            originals = {n: digest(p) for n, p in targets.items()}
            calls = []
            def fail_second(source, target):
                calls.append(target)
                if len(calls) == 2:
                    raise PermissionError("synthetic locked archive")
                return real_replace(source, target)
            with patch("tools.install_menu_pilot.os.replace", side_effect=fail_second):
                with self.assertRaises(PermissionError):
                    replace_pair(sources, targets, {n: digest(p) for n, p in sources.items()}, backups)
            self.assertEqual({n: digest(p) for n, p in targets.items()}, originals)
            self.assertFalse(list(Path(temp).glob("arabic-pilot-*.tmp")))


if __name__ == "__main__":
    unittest.main()
