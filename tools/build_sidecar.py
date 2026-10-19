#!/usr/bin/env python3
"""Build the standalone ``wtob-build`` sidecar with PyInstaller.

The sidecar is intentionally one file so the Tauri bundle can ship a single
resource. ``scipy.linalg`` must stay included because ``scipy.special`` imports
it through ``scipy.ndimage``; the other heavy scientific packages are excluded.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "app" / "src-tauri" / "resources" / "sidecar"
EXCLUDES = (
    "torch",
    "tensorflow",
    "sklearn",
    "pandas",
    "cv2",
    "transformers",
    "datasets",
    "onnxruntime",
    "matplotlib",
    "IPython",
    "pytest",
    "pyarrow",
    "lxml",
    "tkinter",
    "scipy.spatial",
    "scipy.stats",
    "scipy.optimize",
    "scipy.interpolate",
    "scipy.signal",
    "scipy.sparse",
    "scipy.integrate",
    "scipy.fft",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    if os.name != "nt":
        raise SystemExit("the sidecar is a Windows x64 executable")
    data = ROOT / "release_data"
    if not (data / "BUILD_INFO.local.json").is_file() or not (data / "font.ttf").is_file():
        raise SystemExit("release_data is missing; run tools/prepare_release_data.py first")

    DIST.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="wtob-pyinstaller-"))
    try:
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "wtob-build",
            "--distpath",
            str(DIST),
            "--workpath",
            str(work / "build"),
            "--specpath",
            str(work / "spec"),
            "--paths",
            str(ROOT / "tools"),
            "--add-data",
            f"{data};release_data",
        ]
        for module in EXCLUDES:
            command.extend(("--exclude-module", module))
        command.append(str(ROOT / "tools" / "release_build.py"))
        subprocess.run(command, check=True, cwd=ROOT)
        executable = DIST / "wtob-build.exe"
        print(f"built {executable} ({executable.stat().st_size} bytes)")
    finally:
        if args.keep_work:
            print(f"work directory kept at {work}", file=sys.stderr)
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
