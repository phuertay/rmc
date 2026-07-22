#!/usr/bin/env python3
"""Carve typography / Ark token blobs from a xochitl binary.

Looks for:
  - UTF-8 JSON objects containing fontSize / lineHeight / fontFamily
  - qrc path strings under ark-imports
  - token path keys like title.md, body.md

Usage:
  python carve_ark_tokens.py --binary path/to/xochitl --out extracted/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def extract_strings(data: bytes, min_len: int = 6) -> list[str]:
    # printable ASCII + a bit of UTF-8 latin
    pat = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return [m.group().decode("ascii", errors="ignore") for m in pat.finditer(data)]


def find_json_objects(data: bytes) -> list[str]:
    """Heuristic: find { ... } spans that decode as JSON and mention typography."""
    out: list[str] = []
    # only scan around keyword hits to keep it fast
    keys = (b"fontSize", b"lineHeight", b"fontFamily", b"typography", b"title.md", b"body.md")
    hits = set()
    for k in keys:
        start = 0
        while True:
            i = data.find(k, start)
            if i < 0:
                break
            hits.add(max(0, i - 2000))
            start = i + len(k)

    for base in sorted(hits):
        window = data[base : base + 12000]
        # walk braces
        for m in re.finditer(rb"\{", window):
            start = m.start()
            depth = 0
            end = None
            for j in range(start, min(len(window), start + 8000)):
                c = window[j]
                if c == 0x7B:  # {
                    depth += 1
                elif c == 0x7D:  # }
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end is None:
                continue
            raw = window[start:end]
            if b"fontSize" not in raw and b"lineHeight" not in raw and b"typography" not in raw:
                continue
            try:
                text = raw.decode("utf-8")
                obj = json.loads(text)
            except Exception:
                continue
            pretty = json.dumps(obj, indent=2, ensure_ascii=False)
            if pretty not in out:
                out.append(pretty)
            if len(out) >= 80:
                return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if not args.binary.is_file():
        print(f"missing binary: {args.binary}", file=sys.stderr)
        return 1

    data = args.binary.read_bytes()
    print(f"read {args.binary} ({len(data)} bytes)")
    args.out.mkdir(parents=True, exist_ok=True)

    strings = extract_strings(data, 6)
    qrc = sorted({s for s in strings if s.startswith("qrc:/ark") or "ark-imports" in s})
    _write(args.out / "qrc-ark-paths.txt", "\n".join(qrc) + ("\n" if qrc else ""))
    print(f"qrc ark paths: {len(qrc)}")

    tokenish = sorted(
        {
            s
            for s in strings
            if re.search(
                r"fontSize|lineHeight|fontFamily|title\.md|body\.md|title\.lg|Subheading|TitleStyle|typography",
                s,
                re.I,
            )
        }
    )
    _write(args.out / "token-strings.txt", "\n".join(tokenish) + ("\n" if tokenish else ""))
    print(f"token strings: {len(tokenish)}")

    # compact key=value style dumps often appear as QML/JS
    kv = [
        s
        for s in tokenish
        if re.search(r"fontSize\s*[:=]\s*\d|lineHeight\s*[:=]\s*[\d.]", s)
        or ("{" in s and "fontSize" in s)
    ]
    _write(args.out / "fontsize-lines.txt", "\n".join(kv) + ("\n" if kv else ""))
    print(f"fontsize lines: {len(kv)}")

    blobs = find_json_objects(data)
    for i, blob in enumerate(blobs):
        _write(args.out / f"json_blob_{i:03d}.json", blob + "\n")
    _write(args.out / "json_blobs_index.txt", "\n".join(f"json_blob_{i:03d}.json" for i in range(len(blobs))) + "\n")
    print(f"json blobs: {len(blobs)}")

    # summary of numeric fontSize assignments from strings
    nums = []
    for s in strings:
        for m in re.finditer(r"fontSize[\"'\s:=]+(\d+(?:\.\d+)?)", s):
            nums.append((m.group(1), s[:200]))
    _write(
        args.out / "fontsize-numbers.txt",
        "\n".join(f"{n}\t{ctx}" for n, ctx in nums[:500]) + ("\n" if nums else ""),
    )
    print(f"fontsize number hits: {len(nums)}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
