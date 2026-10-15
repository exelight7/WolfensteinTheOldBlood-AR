"""Fetch the pinned, unmodified IBM Arabic font and OFL from IBM's repository."""
import hashlib
from pathlib import Path
import urllib.request


REVISION = "39276912b05f700ee1dd491950c35d8697214208"
BASE = f"https://raw.githubusercontent.com/IBM/plex/{REVISION}/packages/plex-sans-arabic/"
FILES = (
    ("fonts/complete/ttf/IBMPlexSansArabic-Regular.ttf", "IBMPlexSansArabic-Regular.ttf",
     "8e0f1046c736bf939d4939ee3ae0116acf61cbcd6592deae7656761627080981"),
    ("LICENSE.txt", "IBM_Plex_Arabic_OFL.txt",
     "7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da"),
)


def main():
    output = Path("workspace/research")
    output.mkdir(parents=True, exist_ok=True)
    for remote, name, expected in FILES:
        dest = output / name
        data = dest.read_bytes() if dest.exists() else urllib.request.urlopen(BASE + remote, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Hash mismatch for {name}; refusing to use or overwrite file")
        if not dest.exists():
            with dest.open("xb") as stream:
                stream.write(data)
        print(name, expected)


if __name__ == "__main__":
    main()
