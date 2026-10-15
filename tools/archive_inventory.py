"""Read-only experimental reader for the installed WTOB chunk index layout."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib


def read_exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("Truncated index or archive")
    return data


def records(data, archive_size):
    stream = io.BytesIO(data)
    read_exact(stream, 0x24)
    count, unknown = struct.unpack(">II", read_exact(stream, 8))
    if count > len(data) // 37:
        raise ValueError("Implausible entry count")
    result = []
    for ordinal in range(count):
        names = []
        for _ in range(3):
            length = struct.unpack("<I", read_exact(stream, 4))[0]
            if length > len(data) - stream.tell():
                raise ValueError("String exceeds index bounds")
            names.append(read_exact(stream, length).decode("utf-8"))
        metadata_offset = stream.tell()
        offset, size, stored, dependencies = struct.unpack(">IIII", read_exact(stream, 16))
        if offset + stored > archive_size:
            raise ValueError(f"Archive bounds exceeded at entry {ordinal}")
        read_exact(stream, dependencies * 24 + 5)
        result.append(dict(ordinal=ordinal, names=names, offset=offset,
                           size=size, stored=stored, metadata_offset=metadata_offset))
        if ordinal + 1 < count:
            read_exact(stream, 4)
    return result, dict(count=count, unknown=unknown,
                        parsed_bytes=stream.tell(), trailing_bytes=len(data) - stream.tell())


def payload(stream, record):
    stream.seek(record["offset"])
    raw = read_exact(stream, record["stored"])
    if record["size"] == record["stored"]:
        return raw
    decoder = zlib.decompressobj(-15)
    decoded = decoder.decompress(raw, record["size"] + 1)
    # Observed game streams end at a sync-flush boundary, without a final block.
    if not decoder.eof and raw.endswith(b"\x00\x00\xff\xff") and not decoder.unconsumed_tail:
        decoded += decoder.decompress(b"\x03\x00", max(1, record["size"] + 1 - len(decoded)))
    if (len(decoded) != record["size"] or not decoder.eof
            or decoder.unused_data or decoder.unconsumed_tail):
        raise ValueError("Invalid raw DEFLATE stream or declared size")
    return decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("workspace/inventory"))
    args = parser.parse_args()
    game = args.game.resolve(strict=True)
    output = args.output.resolve()
    if output == game or game in output.parents:
        parser.error("Output must be outside the game installation")
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index in sorted((game / "base").glob("chunk*.index")):
        archive = index.with_suffix(".resources")
        entries, summary = records(index.read_bytes(), archive.stat().st_size)
        candidates = [e for e in entries if any(
            term in " ".join(e["names"]).lower()
            for term in ("localiz", ".lang", "font", "strings", "subtitle"))]
        with archive.open("rb") as source:
            for entry in candidates:
                try:
                    content = payload(source, entry)
                except (ValueError, zlib.error) as error:
                    entry["extraction_error"] = str(error)
                    continue
                entry["sha256"] = hashlib.sha256(content).hexdigest()
                # Numeric names avoid trusting archive paths or duplicate resource names.
                (output / f"{index.stem}_{entry['ordinal']:06d}.bin").write_bytes(content)
        (output / f"{index.stem}.local.json").write_text(
            json.dumps(dict(summary=summary, entries=entries), ensure_ascii=False, indent=2),
            encoding="utf-8")
        summaries.append(dict(chunk=index.stem, **summary, candidates=candidates))
        print(index.stem, summary, "candidates", len(candidates))
    (output / "summary.local.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
