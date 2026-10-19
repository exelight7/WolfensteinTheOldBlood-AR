"""Fail a build if the public repository would leak secrets, developer paths,
or proprietary game content.

Two modes:

* ``--git`` (default when a ``.git`` directory exists): inspect exactly the
  files Git tracks, i.e. what a public clone would receive.
* ``--walk``: inspect every file under ``--root`` except well-known ignored
  directories. Used by tests and by CI on an export without history.

Exit code is 0 when clean, 1 when any violation is found. ``--json`` prints a
machine-readable report.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".resources", ".index", ".streamed", ".bimage", ".bfont",
    ".bik", ".pak", ".zip", ".wad", ".pk3", ".ttf", ".otf", ".woff", ".woff2",
}

SKIP_DIRS = {
    ".git", "workspace", "node_modules", "dist", "target", "src-tauri/target",
    "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".serena", "backups",
}

# This file contains the detection patterns themselves.
SKIP_FILES = {"tools/check_public_repo.py"}

# Files that legitimately mention the word "english" or font tools and must be
# exempted from the loose patterns below.
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
]

LOCAL_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\\\?[Uu]sers\\\\?"),
    re.compile(r"[A-Za-z]:\\\\?filessss"),
    re.compile(r"/home/[A-Za-z0-9_.-]+/"),
    re.compile(r"(?i)\bsteamapps\\\\?common\b"),
]

TEXT_LIMIT = 2_000_000
MISSING_ENGLISH_MARKERS = ()


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > TEXT_LIMIT:
            return None
        return path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return None


def collect_git_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True, check=True,
    )
    return [p for p in result.stdout.decode("utf-8", "replace").split("\0") if p]


def collect_walk_files(root: Path) -> list[str]:
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        keep = []
        for d in dirnames:
            rel = d if rel_dir == "." else f"{rel_dir}/{d}"
            if rel in SKIP_DIRS or d in SKIP_DIRS:
                continue
            keep.append(d)
        dirnames[:] = keep
        for name in filenames:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            files.append(rel)
    return files


def scan_translation_english(root: Path, rel: str) -> list[str]:
    findings: list[str] = []
    if not rel.startswith("translation/arabic/") or not rel.endswith(".json"):
        return findings
    text = _read_text(root / rel)
    if text is None:
        return findings
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return findings
    if isinstance(data, list):
        leaks = [r.get("id", "?") for r in data
                 if isinstance(r, dict) and str(r.get("english", "")).strip()]
        if leaks:
            findings.append(f"{rel}: {len(leaks)} record(s) carry English text "
                            f"(first: {leaks[0]})")
    return findings


def scan_file(root: Path, rel: str) -> list[str]:
    findings: list[str] = []
    path = root / rel
    ext = path.suffix.lower()
    if ext in FORBIDDEN_EXTENSIONS:
        findings.append(f"{rel}: forbidden proprietary/binary extension ({ext})")
        return findings
    text = _read_text(path)
    if text is None:
        return findings
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"{rel}: possible secret ({pattern.pattern})")
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(text):
            findings.append(f"{rel}: developer absolute path ({pattern.pattern})")
    findings.extend(scan_translation_english(root, rel))
    return findings


def scan(root: Path, files: list[str]) -> list[str]:
    findings: list[str] = []
    for rel in files:
        if rel.replace("\\", "/") in SKIP_FILES:
            continue
        findings.extend(scan_file(root, rel))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--walk", action="store_true",
                        help="walk the tree instead of using git ls-files")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    use_git = not args.walk and (root / ".git").is_dir()
    files = collect_git_files(root) if use_git else collect_walk_files(root)
    findings = scan(root, files)

    report = {
        "root": str(root),
        "mode": "git" if use_git else "walk",
        "files_scanned": len(files),
        "violations": findings,
        "clean": not findings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"check_public_repo: {report['mode']} mode, "
              f"{len(files)} files, {len(findings)} violation(s)")
        for item in findings:
            print(f"  FAIL {item}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
