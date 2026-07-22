#!/usr/bin/env python3
"""Convert .woff / .woff2 to .ttf (needs fonttools + brotli).

  python scripts/woff2_to_ttf.py in.woff2 [out.ttf]
  python scripts/woff2_to_ttf.py --dir some/folder   # all woff2 in dir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def convert(src: Path, dst: Path | None = None) -> Path:
    try:
        from fontTools.ttLib import TTFont
    except ImportError as e:
        raise SystemExit(
            "need fonttools + brotli:  pip install fonttools brotli\n" + str(e)
        ) from e
    if dst is None:
        dst = src.with_suffix(".ttf")
    font = TTFont(str(src))
    # Without this, save() keeps woff2 packaging → Windows "not a valid font".
    font.flavor = None
    font.save(str(dst))
    raw = dst.read_bytes()[:4]
    if raw not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"):
        dst.unlink(missing_ok=True)
        raise SystemExit(f"converted file not sfnt (magic={raw!r}): {src}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, nargs="?", help="input .woff2")
    ap.add_argument("dst", type=Path, nargs="?", help="output .ttf")
    ap.add_argument("--dir", type=Path, help="convert all .woff/.woff2 in directory")
    args = ap.parse_args()
    if args.dir:
        n = 0
        for p in sorted(args.dir.glob("*.woff*")):
            if p.suffix.lower() not in {".woff", ".woff2"}:
                continue
            out = convert(p)
            print(f"{p.name} -> {out.name}")
            n += 1
        return 0 if n else 1
    if not args.src:
        ap.print_help()
        return 2
    out = convert(args.src, args.dst)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
