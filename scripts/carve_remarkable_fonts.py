#!/usr/bin/env python3
"""Carve reMarkable sfnt fonts (ttf/otf) out of a binary (e.g. xochitl RCC).

  python scripts/carve_remarkable_fonts.py --binary path/to/xochitl --out fonts/

Never commits carved fonts. Device faces are proprietary — local install only.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

MAGICS = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1")
NEEDLE = b"reMarkable"


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from(">H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from(">I", data, off)[0]


def _sfnt_end(data: bytes, start: int) -> int | None:
    """Return exclusive end offset of sfnt at start, or None if invalid."""
    if start + 12 > len(data):
        return None
    if data[start : start + 4] not in MAGICS:
        return None
    ntables = _u16(data, start + 4)
    if ntables < 1 or ntables > 64:
        return None
    end = start + 12 + ntables * 16
    if end > len(data):
        return None
    for i in range(ntables):
        ent = start + 12 + i * 16
        off = _u32(data, ent + 8)
        length = _u32(data, ent + 12)
        if off > len(data) or length > len(data):
            return None
        end = max(end, start + off + length)
    if end > len(data) or end - start < 1000 or end - start > 8_000_000:
        return None
    return end


def _name_blob(data: bytes, start: int, end: int) -> bytes:
    ntables = _u16(data, start + 4)
    for i in range(ntables):
        ent = start + 12 + i * 16
        tag = data[ent : ent + 4]
        if tag != b"name":
            continue
        off = start + _u32(data, ent + 8)
        length = _u32(data, ent + 12)
        return data[off : off + length]
    return b""


def _safe_stem(name_blob: bytes, default: str) -> str:
    """Prefer PostScript / full font name containing reMarkable."""
    # crude: pull printable ASCII runs with reMarkable
    text = name_blob.replace(b"\x00", b"")
    best = ""
    for part in text.split(b"\xff"):
        if NEEDLE not in part:
            continue
        s = "".join(chr(c) if 32 <= c < 127 else " " for c in part)
        for tok in s.replace("/", " ").split():
            if "reMarkable" in tok and len(tok) > len(best):
                best = tok
    if best:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in best)[:80]
    return default


def carve(data: bytes, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    seen: set[tuple[int, int]] = set()
    start = 0
    while True:
        hits = [data.find(m, start) for m in MAGICS]
        hits = [h for h in hits if h >= 0]
        if not hits:
            break
        i = min(hits)
        end = _sfnt_end(data, i)
        if end is None:
            start = i + 4
            continue
        blob = data[i:end]
        if NEEDLE not in blob:
            start = i + 4
            continue
        key = (i, end)
        if key in seen:
            start = i + 4
            continue
        seen.add(key)
        ext = ".otf" if blob[:4] == b"OTTO" else ".ttf"
        stem = _safe_stem(_name_blob(data, i, end), f"reMarkable_{i:x}")
        path = out / f"{stem}{ext}"
        n = 1
        while path.exists():
            path = out / f"{stem}_{n}{ext}"
            n += 1
        path.write_bytes(blob)
        written.append(path)
        start = end
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    data = args.binary.read_bytes()
    paths = carve(data, args.out)
    print(f"carved {len(paths)} font(s) -> {args.out}")
    for p in paths:
        print(f"  {p.name}  {p.stat().st_size}")
    return 0 if paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
