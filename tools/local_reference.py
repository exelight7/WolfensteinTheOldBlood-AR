"""Generate an untranslated bilingual reference from a locally extracted .lang."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


TOKEN = re.compile(r'\s+|//[^\r\n]*|"(?:[^"\\]|\\["n])*"|[{}]')


def parse_lang(raw):
    text = raw.decode("utf-8-sig")
    tokens = []
    cursor = 0
    for match in TOKEN.finditer(text):
        if match.start() != cursor:
            raise ValueError(f"Unsupported syntax at character {cursor}")
        cursor = match.end()
        token = match.group()
        if not token.isspace() and not token.startswith("//"):
            tokens.append(token)
    if cursor != len(text) or not tokens or tokens[0] != "{" or tokens[-1] != "}":
        raise ValueError("Invalid table boundaries")
    body = tokens[1:-1]
    if len(body) % 2 or any(not t.startswith('"') for t in body):
        raise ValueError("Expected quoted key/value pairs")
    rows = []
    seen = set()
    for index in range(0, len(body), 2):
        key, value = body[index:index + 2]
        key = key[1:-1]
        if not key.startswith("#str_") or key in seen or "\\" in key:
            raise ValueError(f"Invalid or duplicate source ID: {key}")
        seen.add(key)
        source_literal = value[1:-1]
        english = re.sub(r'\\(["n])', lambda m: '\n' if m[1] == 'n' else '"', source_literal)
        rows.append(dict(id="strings/english.lang:" + key, source_key=key,
                         resource="strings/english.lang", index=index // 2,
                         english=english, english_literal=source_literal,
                         english_sha256=hashlib.sha256(english.encode("utf-8")).hexdigest(),
                         arabic="", status="untranslated", context="Unknown"))
    return rows


def generate(raw, output):
    rows = parse_lang(raw)
    existing = output / "translation_master.local.jsonl"
    if existing.exists():
        previous_rows = [json.loads(line) for line in existing.read_text(encoding="utf-8").splitlines() if line]
        previous = {row["id"]: row for row in previous_rows}
        if len(previous) != len(previous_rows) or set(previous) != {row["id"] for row in rows}:
            raise ValueError("Source IDs changed; explicit migration required")
        for row in rows:
            old = previous[row["id"]]
            if old["english_sha256"] != row["english_sha256"] or old["english"] != row["english"]:
                raise ValueError("English source changed; explicit migration required")
            row.update({key: value for key, value in old.items() if key not in row or key in ("arabic", "status", "context")})
    output.mkdir(parents=True, exist_ok=True)
    master = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    reference = "# Local bilingual reference\n\n"
    for row in rows:
        reference += (f"## ID: {row['id']}\n\nRESOURCE: {row['resource']}\n"
                      f"INDEX: {row['index']}\nSTATUS: {row['status']}\n\n"
                      f"AR:\n{row['arabic']}\n\nEN:\n{row['english']}\n\nCONTEXT: Unknown\n\n")
    (output / "translation_master.local.jsonl").write_text(master, encoding="utf-8", newline="\n")
    (output / "ALL_TRANSLATIONS.local.md").write_text(reference, encoding="utf-8", newline="\n")
    # Keep the immutable input for lossless serialization and later round-trip tests.
    (output / "english_source.local.lang").write_bytes(raw)
    duplicates = Counter(row["english"] for row in rows)
    summary = dict(entries=len(rows), unique_ids=len(rows),
                   empty_values=sum(not row["english"] for row in rows),
                   duplicate_value_groups=sum(n > 1 for n in duplicates.values()),
                   source_sha256=hashlib.sha256(raw).hexdigest())
    (output / "summary.local.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reference"))
    args = parser.parse_args()
    print(json.dumps(generate(args.source.read_bytes(), args.output), indent=2))


if __name__ == "__main__":
    main()
