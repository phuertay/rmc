#!/usr/bin/env python3
"""Extract Qt RCC resource trees from a binary (e.g. xochitl).

Name-table + tree heuristics (qtrc-extract style) plus standalone `qres` blobs.

Usage:
  python extract_qt_rcc.py --binary path/to/xochitl --out extracted/rcc
  python extract_qt_rcc.py --self-check
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

EXTRACTOR_REV = "2026-07-22-controls-near-names"

FLAG_COMPRESSED = 0x01
FLAG_DIRECTORY = 0x02
FLAG_COMPRESSED_ZSTD = 0x04


def qhash(s: str) -> int:
    h = 0
    for c in s:
        h = (h << 4) + ord(c)
        g = h & 0xF0000000
        if g:
            h ^= g >> 23
        h &= ~g
    return h & 0xFFFFFFFF


def encode_name(name: str) -> bytes:
    utf = name.encode("utf-16-be")
    return struct.pack(">HI", len(name), qhash(name)) + utf


def parse_name_at(data: bytes, off: int, *, allow_empty: bool = False) -> tuple[str, int] | None:
    if off + 6 > len(data):
        return None
    size = struct.unpack_from(">H", data, off)[0]
    h = struct.unpack_from(">I", data, off + 2)[0]
    # Qt root is often the empty string: size=0, hash=0 — only when explicitly allowed
    if size == 0:
        if allow_empty and h == 0:
            return "", off + 6
        return None
    if size > 512:
        return None
    end = off + 6 + size * 2
    if end > len(data):
        return None
    chars = struct.unpack_from(">" + "H" * size, data, off + 6)
    try:
        name = "".join(chr(c) for c in chars)
    except ValueError:
        return None
    if any(ord(c) < 0x20 and c not in "\t\n\r" for c in name):
        return None
    if qhash(name) != h:
        return None
    return name, end


def scan_name_sections(data: bytes) -> list[tuple[range, dict[int, str]]]:
    hits: set[int] = set()
    for align in (0, 1):
        i = align
        while i + 8 < len(data):
            if data[i] == 0 and 0x20 <= data[i + 1] < 0x7F:
                start_char = i
                j = i
                while j + 1 < len(data) and data[j] == 0 and 0x20 <= data[j + 1] < 0x7F:
                    j += 2
                run = (j - start_char) // 2
                if run >= 1:
                    cand = start_char - 6
                    if cand >= 0 and cand not in hits and parse_name_at(data, cand):
                        hits.add(cand)
                        # empty root name often sits immediately before first real name
                        if cand >= 6 and parse_name_at(data, cand - 6, allow_empty=True) == ("", cand):
                            hits.add(cand - 6)
                i = j
            else:
                i += 2

    used: set[int] = set()
    sections: list[tuple[range, dict[int, str]]] = []
    for off in sorted(hits):
        if off in used:
            continue
        names: dict[int, str] = {}
        cur = off
        # leading empty only
        first = parse_name_at(data, cur, allow_empty=True)
        if first and first[0] == "":
            names[0] = ""
            used.update(range(cur, first[1]))
            cur = first[1]
        while True:
            parsed = parse_name_at(data, cur)  # non-empty only
            if not parsed:
                break
            name, nxt = parsed
            names[cur - off] = name
            used.update(range(cur, nxt))
            cur = nxt
            if len(names) > 5000:
                break
        if len(names) >= 2:
            sections.append((range(off, cur), names))
    return sections


def entry_size(version: int) -> int:
    return 14 if version == 1 else 22


def read_entry(data: bytes, base: int, node_id: int, version: int):
    es = entry_size(version)
    off = base + node_id * es
    if off + es > len(data):
        return None
    name_offset, flags = struct.unpack_from(">IH", data, off)
    a, b = struct.unpack_from(">II", data, off + 6)
    if flags & ~0x07:
        return None
    return name_offset, flags, a, b


def parse_tree(
    data: bytes,
    base: int,
    names: dict[int, str],
    node_id: int,
    count: int,
    version: int,
    seen: set[int],
) -> list | None:
    out: list = []
    es = entry_size(version)
    if base + (node_id + count) * es > len(data):
        return None
    for nid in range(node_id, node_id + count):
        if nid in seen:
            return None
        seen.add(nid)
        ent = read_entry(data, base, nid, version)
        if ent is None:
            return None
        name_off, flags, a, b = ent
        if name_off not in names:
            return None
        name = names[name_off]
        if flags & FLAG_DIRECTORY:
            child_count, first_child = a, b
            if child_count > 10_000:
                return None
            kids = parse_tree(data, base, names, first_child, child_count, version, seen)
            if kids is None:
                return None
            out.append((name, flags, None, kids))
        else:
            out.append((name, flags, b, None))
    return out


def walk_files(nodes: list, prefix: tuple[str, ...] = ()) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for name, flags, data_off, kids in nodes:
        path = prefix + (name,)
        if kids is not None:
            found.extend(walk_files(kids, path))
        elif data_off is not None:
            found.append(("/".join(path), flags, data_off))
    return found


def try_tree_at(
    data: bytes, tree_base: int, names: dict[int, str], version: int
) -> list[tuple[str, int, int]] | None:
    seen: set[int] = set()
    nodes = parse_tree(data, tree_base, names, 0, 1, version, seen)
    if not nodes:
        return None
    # Prefer full name-table coverage; allow small slack for trailing junk names.
    if len(seen) < max(2, len(names) - 2) and len(seen) != len(names):
        return None
    if len(seen) > len(names):
        return None
    files = walk_files(nodes)
    return files or None


def find_tree_bases(
    data: bytes,
    name_range: range,
    names: dict[int, str],
    *,
    full_scan: bool = False,
) -> list[tuple[int, int, list]]:
    """Locate tree by scanning for directory entries whose name_offset is in this table."""
    hits: list[tuple[int, int, list]] = []
    # Trees often sit immediately after the name table (tokens/controls pattern).
    windows = [
        range(name_range.stop, min(len(data), name_range.stop + 4096)),
        range(max(0, name_range.start - 2_000_000), name_range.start),
        range(name_range.stop, min(len(data), name_range.stop + 2_000_000)),
    ]
    if full_scan:
        windows.append(range(0, len(data)))

    preferred = []
    for off, name in names.items():
        if name in ("", "ark-imports", "ark", "qt", "tokens", "qml", "controls"):
            preferred.append(off)
    root_candidates = preferred + [o for o in names if o not in preferred]

    for version in (3, 2, 1):
        es = entry_size(version)
        for name_off in root_candidates:
            needle = struct.pack(">I", name_off)
            for win in windows:
                start = win.start
                checked = 0
                while checked < 5000:
                    i = data.find(needle, start, win.stop)
                    if i < 0:
                        break
                    checked += 1
                    if i + es <= len(data):
                        ent = read_entry(data, i, 0, version)
                        if ent is not None:
                            noff, flags, a, _b = ent
                            if (
                                noff == name_off
                                and (flags & FLAG_DIRECTORY)
                                and 1 <= a <= len(names) + 5
                            ):
                                files = try_tree_at(data, i, names, version)
                                if files is not None:
                                    hits.append((version, i, files))
                                    return hits
                    start = i + 1
    return hits


def decompress_blob(payload: bytes, flags: int) -> bytes:
    if flags & FLAG_COMPRESSED_ZSTD:
        try:
            import zstandard  # type: ignore

            dctx = zstandard.ZstdDecompressor()
            for candidate in (payload, payload[4:] if len(payload) > 4 else payload):
                try:
                    return dctx.decompress(candidate, max_output_size=5_000_000)
                except Exception:
                    continue
        except Exception:
            pass
        return payload
    if flags & FLAG_COMPRESSED:
        if len(payload) < 4:
            return payload
        try:
            return zlib.decompress(payload[4:])
        except zlib.error:
            try:
                return zlib.decompress(payload)
            except zlib.error:
                return payload
    return payload


def read_blob(data: bytes, blob_base: int, data_offset: int) -> bytes | None:
    off = blob_base + data_offset
    if off + 4 > len(data):
        return None
    size = struct.unpack_from(">I", data, off)[0]
    if size == 0 or size > 50_000_000 or off + 4 + size > len(data):
        return None
    return data[off + 4 : off + 4 + size]


def infer_blob_base(
    data: bytes,
    files: list[tuple[str, int, int]],
    hint_lo: int,
    hint_hi: int,
) -> int | None:
    # Duplicate data_offsets are normal (aliases); unique-sort for the size chain.
    offs = sorted({d for _, _, d in files})
    lo = max(0, hint_lo)
    hi = min(len(data), hint_hi)

    def try_window(wlo: int, whi: int) -> int | None:
        if len(offs) >= 2:
            deltas = [offs[i + 1] - offs[i] - 4 for i in range(len(offs) - 1)]
            if any(d <= 0 or d > 50_000_000 for d in deltas):
                return None
            # Prefer full chain; fall back to long prefix (last blob size unknown).
            for n in range(len(deltas), 2, -1):
                needle = struct.pack(">I", deltas[0])
                start = wlo
                while start < whi:
                    i = data.find(needle, start, whi)
                    if i < 0:
                        break
                    base = i - offs[0]
                    if base >= 0:
                        good = True
                        for j in range(n):
                            payload = read_blob(data, base, offs[j])
                            if payload is None or len(payload) != deltas[j]:
                                good = False
                                break
                        if good and read_blob(data, base, offs[-1]) is not None:
                            return base
                    start = i + 1
            return None
        only = offs[0]
        step = 4 if (whi - wlo) < 4_000_000 else 16
        for base in range(wlo, whi, step):
            payload = read_blob(data, base, only)
            if payload is not None and 0 < len(payload) < 5_000_000:
                return base
        if read_blob(data, 0, only) is not None:
            return 0
        return None

    found = try_window(lo, hi)
    if found is not None:
        return found
    if lo > 0 or hi < len(data):
        return try_window(0, len(data))
    return None


def looks_like_text(body: bytes) -> bool:
    if not body:
        return False
    sample = body[:4096]
    # UTF-8 / ASCII heavy
    printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126)
    return printable / len(sample) > 0.85


def extract_qres_file(data: bytes, off: int, out_dir: Path) -> int:
    if data[off : off + 4] != b"qres" or off + 20 > len(data):
        return 0
    version, tree_off, data_off, names_off = struct.unpack_from(">IIII", data, off + 4)
    if version not in (1, 2, 3):
        return 0
    if max(tree_off, data_off, names_off) >= len(data) - off:
        return 0
    names_abs = off + names_off
    tree_abs = off + tree_off
    blob_abs = off + data_off
    names: dict[int, str] = {}
    cur = names_abs
    first = parse_name_at(data, cur, allow_empty=True)
    if first and first[0] == "":
        names[0] = ""
        cur = first[1]
    while cur < len(data):
        parsed = parse_name_at(data, cur)
        if not parsed:
            break
        name, nxt = parsed
        names[cur - names_abs] = name
        cur = nxt
        if len(names) > 5000:
            break
    if not names:
        return 0
    files = try_tree_at(data, tree_abs, names, version)
    if not files:
        return 0
    n = 0
    for path, flags, dop in files:
        raw = read_blob(data, blob_abs, dop)
        if raw is None:
            continue
        body = decompress_blob(raw, flags)
        dest = out_dir / "qres" / f"off_{off:x}" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        n += 1
    return n


def interesting(names: dict[int, str]) -> bool:
    blob = " ".join(names.values()).lower()
    # prefer design-token / typography trees; avoid icon-only "ark/icons" noise
    return any(
        k in blob
        for k in (
            "ark-imports",
            "token",
            "typography",
            "fontsize",
            "title.md",
            "body.md",
            "label.md",
            "subheading",
        )
    )


def name_table_variants(
    nrange: range, names: dict[int, str]
) -> list[tuple[range, dict[int, str], str]]:
    """Try names base with/without a leading empty root (offset shift by 6)."""
    out: list[tuple[range, dict[int, str], str]] = [
        (nrange, names, "as-scanned"),
    ]
    if names.get(0) == "":
        shifted = {k - 6: v for k, v in names.items() if k >= 6}
        if shifted:
            out.append(
                (
                    range(nrange.start + 6, nrange.stop),
                    shifted,
                    "drop-leading-empty",
                )
            )
    elif "" not in names.values():
        # try prepending synthetic empty at base-6 if bytes match
        out.append((nrange, names, "no-empty"))
    return out


def carve_compressed_text(data: bytes, out: Path) -> list[str]:
    """Fallback: decompress qCompress/zlib/zstd islands that look like tokens/QML."""
    hits: list[str] = []
    dest = out / "carved"
    dest.mkdir(parents=True, exist_ok=True)
    # qCompress: 4-byte BE uncompressed len + zlib
    for magic in (b"\x78\x9c", b"\x78\xda", b"\x78\x01", b"\x78\x5e"):
        start = 0
        while True:
            i = data.find(magic, start)
            if i < 0 or i < 4:
                break
            # try as qCompress (size at i-4) or raw zlib at i
            for zoff, with_size in ((i - 4, True), (i, False)):
                try:
                    if with_size:
                        ulen = struct.unpack_from(">I", data, zoff)[0]
                        if ulen < 8 or ulen > 5_000_000:
                            continue
                        body = zlib.decompress(data[zoff + 4 :])
                        if abs(len(body) - ulen) > 16 and ulen < 10_000_000:
                            # size hint mismatch — still keep if text looks good
                            pass
                    else:
                        body = zlib.decompress(data[zoff:])
                except Exception:
                    continue
                if not looks_like_text(body):
                    continue
                text = body.decode("utf-8", errors="ignore")
                if not any(
                    k in text
                    for k in ("fontSize", "lineHeight", "fontFamily", "typography", "ark-imports")
                ):
                    continue
                path = dest / f"zlib_{zoff:x}.txt"
                path.write_bytes(body)
                hits.append(str(path.relative_to(out)))
                break
            start = i + 1
            if len(hits) >= 80:
                return hits
    # zstd magic 28 b5 2f fd
    start = 0
    try:
        import zstandard

        dctx = zstandard.ZstdDecompressor()
    except Exception:
        dctx = None
    if dctx is not None:
        while True:
            i = data.find(b"\x28\xb5\x2f\xfd", start)
            if i < 0:
                break
            try:
                body = dctx.decompress(data[i : i + 2_000_000], max_output_size=5_000_000)
            except Exception:
                start = i + 1
                continue
            if looks_like_text(body):
                text = body.decode("utf-8", errors="ignore")
                if any(k in text for k in ("fontSize", "lineHeight", "fontFamily", "typography")):
                    path = dest / f"zstd_{i:x}.txt"
                    path.write_bytes(body)
                    hits.append(str(path.relative_to(out)))
            start = i + 1
            if len(hits) >= 80:
                break
    return hits


def diagnose_name_table(
    data: bytes, nrange: range, names: dict[int, str], label: str
) -> list[str]:
    """Explain why tree matching fails for a name table."""
    lines = [
        f"## {label} names@0x{nrange.start:x}-0x{nrange.stop:x} count={len(names)}",
        "names: " + ", ".join(("∅" if not n else n) for n in list(names.values())[:20]),
    ]
    root_candidates = []
    for off, name in names.items():
        if name in ("", "ark-imports", "ark", "qt", "tokens", "qml"):
            root_candidates.append((off, name))
    root_candidates += [(o, names[o]) for o in names if o not in {c[0] for c in root_candidates}]
    root_candidates = root_candidates[:8]

    for version in (3, 2, 1):
        es = entry_size(version)
        for name_off, name in root_candidates:
            needle = struct.pack(">I", name_off)
            needle_le = struct.pack("<I", name_off)
            for endian, nd in (("BE", needle), ("LE", needle_le)):
                positions = []
                start = 0
                while len(positions) < 30:
                    i = data.find(nd, start)
                    if i < 0:
                        break
                    positions.append(i)
                    start = i + 1
                dir_ok = 0
                tree_ok = 0
                fail_seen = []
                for i in positions:
                    if endian == "LE":
                        continue  # only probe BE entries for full parse
                    ent = read_entry(data, i, 0, version)
                    if ent is None:
                        continue
                    noff, flags, a, _b = ent
                    if noff != name_off or not (flags & FLAG_DIRECTORY):
                        continue
                    if not (1 <= a <= len(names) + 5):
                        continue
                    dir_ok += 1
                    seen: set[int] = set()
                    nodes = parse_tree(data, i, names, 0, 1, version, seen)
                    if nodes is None:
                        fail_seen.append(f"0x{i:x}:parse_fail flags={flags} children={a}")
                        continue
                    if len(seen) != len(names) and len(seen) < max(2, len(names) - 2):
                        fail_seen.append(
                            f"0x{i:x}:seen={len(seen)}/{len(names)} children={a}"
                        )
                        continue
                    files = walk_files(nodes)
                    if files:
                        tree_ok += 1
                        fail_seen.append(
                            f"0x{i:x}:TREE_OK files={len(files)} seen={len(seen)}"
                        )
                lines.append(
                    f"  v{version} root={name!r}@rel={name_off} {endian}: "
                    f"hits={len(positions)} dir_ok={dir_ok} tree_ok={tree_ok}"
                )
                for fs in fail_seen[:8]:
                    lines.append(f"    {fs}")
    return lines


def dump_focus_slices(data: bytes, sections: list, out: Path) -> list[str]:
    """Write binary slices around ark-imports name tables for offline debug."""
    slice_dir = out / "slices"
    slice_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    focuses = [
        (r, names)
        for r, names in sections
        if "ark-imports" in " ".join(names.values()).lower()
    ]
    if not focuses:
        return written
    lo = min(r.start for r, _ in focuses) - 2_000_000
    hi = max(r.stop for r, _ in focuses) + 2_000_000
    lo = max(0, lo)
    hi = min(len(data), hi)
    path = slice_dir / f"around_ark_imports_{lo:x}_{hi:x}.bin"
    path.write_bytes(data[lo:hi])
    meta = slice_dir / "SLICES.txt"
    meta.write_text(
        "\n".join(
            [
                f"extractor={EXTRACTOR_REV}",
                f"file_size={len(data)}",
                f"slice={path.name} file_off=0x{lo:x}-0x{hi:x} len={hi-lo}",
                "sections:",
                *[
                    f"  0x{r.start:x}-0x{r.stop:x} ({len(n)}): "
                    + ", ".join(("∅" if not x else x) for x in list(n.values())[:15])
                    for r, n in focuses
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.extend([path.name, meta.name])
    return written


def extract_all(
    data: bytes,
    out: Path,
    prefer_interesting: bool = True,
    focus: str | None = None,
) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {
        "extractor_rev": EXTRACTOR_REV,
        "qres_files": 0,
        "trees": 0,
        "files": 0,
        "interesting_trees": [],
        "failed_interesting": [],
        "carved": 0,
        "slices": 0,
    }
    fail_lines: list[str] = []
    diag_lines: list[str] = [f"extractor_rev={EXTRACTOR_REV}", f"file_size={len(data)}"]

    start = 0
    while True:
        i = data.find(b"qres", start)
        if i < 0:
            break
        summary["qres_files"] += extract_qres_file(data, i, out)
        start = i + 4

    sections = scan_name_sections(data)
    (out / "name_sections.txt").write_text(
        "\n".join(
            f"0x{r.start:x}-0x{r.stop:x} ({len(names)} names): "
            + ", ".join(
                ("∅" if not n else n) for n in list(names.values())[:40]
            )
            + ("…" if len(names) > 40 else "")
            for r, names in sections
        )
        + "\n",
        encoding="utf-8",
    )

    ordered = sorted(sections, key=lambda sn: (0 if interesting(sn[1]) else 1, -len(sn[1])))
    for idx, (nrange, names) in enumerate(ordered):
        name_blob = " ".join(names.values()).lower()
        if focus and focus.lower() not in name_blob:
            continue
        is_interesting = interesting(names)
        if prefer_interesting and not is_interesting and not focus and summary["trees"] >= 3:
            continue

        found = None
        used_variant = ""
        used_names = names
        used_range = nrange
        for vr, vn, vlabel in name_table_variants(nrange, names):
            trees = find_tree_bases(
                data, vr, vn, full_scan=is_interesting or bool(focus)
            )
            if trees:
                found = trees[0]
                used_variant = vlabel
                used_names = vn
                used_range = vr
                break
        if not found:
            if is_interesting or focus:
                msg = (
                    f"no tree for names@0x{nrange.start:x} ({len(names)} names): "
                    f"{list(names.values())[:12]}"
                )
                fail_lines.append(msg)
                summary["failed_interesting"].append(msg)
                for vr, vn, vlabel in name_table_variants(nrange, names):
                    diag_lines.extend(
                        diagnose_name_table(data, vr, vn, f"{vlabel}")
                    )
            continue
        version, tree_base, files = found
        blob_base = infer_blob_base(
            data,
            files,
            hint_lo=min(used_range.start, tree_base) - 500_000,
            hint_hi=max(used_range.stop, tree_base) + 2_000_000,
        )
        if blob_base is None:
            if is_interesting or focus:
                msg = f"no blob for tree@0x{tree_base:x} names@0x{used_range.start:x} files={len(files)} variant={used_variant}"
                fail_lines.append(msg)
                summary["failed_interesting"].append(msg)
            continue
        tree_dir = out / f"tree_{idx:03d}_v{version}_{tree_base:x}"
        tree_dir.mkdir(parents=True, exist_ok=True)
        wrote = 0
        textish = 0
        for path, flags, dop in files:
            raw = read_blob(data, blob_base, dop)
            if raw is None:
                continue
            body = decompress_blob(raw, flags)
            dest = tree_dir / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            wrote += 1
            if looks_like_text(body):
                textish += 1
        (tree_dir / "_meta.txt").write_text(
            "\n".join(
                [
                    f"version={version}",
                    f"tree_base=0x{tree_base:x}",
                    f"blob_base=0x{blob_base:x}",
                    f"names=0x{used_range.start:x}-0x{used_range.stop:x}",
                    f"variant={used_variant}",
                    f"file_count={len(files)}",
                    f"wrote={wrote}",
                    f"textish={textish}",
                    "names: "
                    + ", ".join(("∅" if not n else n) for n in used_names.values()),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        if textish == 0 and wrote > 0 and is_interesting:
            msg = f"rejected garbage tree@0x{tree_base:x} (0 textish of {wrote})"
            fail_lines.append(msg)
            summary["failed_interesting"].append(msg)
            continue
        summary["trees"] += 1
        summary["files"] += wrote
        if is_interesting:
            summary["interesting_trees"].append(tree_dir.name)

    carved = carve_compressed_text(data, out)
    summary["carved"] = len(carved)

    slices = dump_focus_slices(data, sections, out)
    summary["slices"] = len(slices)

    hits: list[str] = []
    for p in out.rglob("*"):
        if not p.is_file() or p.name.startswith("_"):
            continue
        if p.suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".woff",
            ".woff2",
            ".qm",
            ".ico",
            ".ttf",
        }:
            continue
        if p.stat().st_size > 2_000_000:
            continue
        raw = p.read_bytes()
        if not looks_like_text(raw):
            continue
        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if not any(
            k in text
            for k in ("fontSize", "lineHeight", "font-size", "typography", "fontFamily")
        ):
            continue
        for line in text.splitlines():
            if any(
                k in line
                for k in ("fontSize", "lineHeight", "font-size", "fontFamily")
            ):
                hits.append(f"{p.relative_to(out)}: {line.strip()[:200]}")
                if len(hits) >= 500:
                    break
        if len(hits) >= 500:
            break
    (out / "typography_hits.txt").write_text(
        "\n".join(hits) + ("\n" if hits else ""), encoding="utf-8"
    )
    summary["typography_hits"] = len(hits)
    if fail_lines:
        (out / "FAILED.txt").write_text("\n".join(fail_lines) + "\n", encoding="utf-8")
    if len(diag_lines) > 2:
        (out / "DIAGNOSE.txt").write_text("\n".join(diag_lines) + "\n", encoding="utf-8")
    (out / "SUMMARY.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in summary.items()) + "\n", encoding="utf-8"
    )
    return summary


def build_synthetic_qres() -> bytes:
    """Minimal v2 qres: /ark-imports/tokens/title.md with JSON body."""
    body = b'{"fontSize":42,"lineHeight":1.2,"fontFamily":"EB Garamond"}\n'
    # names: "", "ark-imports", "tokens", "title.md" — root name is often empty in real trees;
    # use "ark-imports" as root dir for simplicity
    name_ark = encode_name("ark-imports")
    name_tok = encode_name("tokens")
    name_file = encode_name("title.md")
    names = name_ark + name_tok + name_file
    # name offsets: 0, len(name_ark), len(name_ark)+len(name_tok)
    off_ark, off_tok, off_file = 0, len(name_ark), len(name_ark) + len(name_tok)

    # blobs: one uncompressed file at data_offset 0
    blob = struct.pack(">I", len(body)) + body

    # tree entries v2 (22 bytes): root dir -> tokens dir -> title.md file
    # node 0: ark-imports dir, children=1, first=1
    # node 1: tokens dir, children=1, first=2
    # node 2: title.md file, locale=0, data_offset=0
    def dir_ent(name_off: int, count: int, first: int) -> bytes:
        return struct.pack(">IHIIQ", name_off, FLAG_DIRECTORY, count, first, 0)

    def file_ent(name_off: int, data_off: int) -> bytes:
        return struct.pack(">IHIIQ", name_off, 0, 0, data_off, 0)

    tree = dir_ent(off_ark, 1, 1) + dir_ent(off_tok, 1, 2) + file_ent(off_file, 0)

    # qres header: magic, version, tree_off, data_off, names_off
    header_len = 20
    tree_off = header_len
    data_off = tree_off + len(tree)
    names_off = data_off + len(blob)
    header = b"qres" + struct.pack(">IIII", 2, tree_off, data_off, names_off)
    return header + tree + blob + names


def self_check() -> int:
    import tempfile

    blob = build_synthetic_qres()
    # bury inside padding to mimic embedded binary
    data = b"\x00" * 1000 + blob + b"\x00" * 1000
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        summary = extract_all(data, out, prefer_interesting=False)
        hits = (out / "typography_hits.txt").read_text(encoding="utf-8")
        bodies = [p.read_text(encoding="utf-8") for p in out.rglob("title.md")]
        ok = summary["qres_files"] >= 1 and any('"fontSize":42' in b for b in bodies)
        print(f"self-check: {'PASS' if ok else 'FAIL'} summary={summary}")
        print(f"hits:\n{hits}")
        return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--all", action="store_true", help="extract non-interesting trees too")
    ap.add_argument(
        "--focus",
        default="ark-imports",
        help="only name tables containing this substring (default: ark-imports; empty=all)",
    )
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    if args.self_check:
        return self_check()
    if not args.binary or not args.out:
        ap.error("--binary and --out required (or --self-check)")
    if not args.binary.is_file():
        print(f"missing binary: {args.binary}")
        return 1
    data = args.binary.read_bytes()
    print(f"read {args.binary} ({len(data)} bytes)")
    focus = args.focus.strip() or None
    summary = extract_all(
        data,
        args.out,
        prefer_interesting=not args.all,
        focus=focus,
    )
    print(f"extractor_rev={EXTRACTOR_REV}")
    print(f"trees={summary['trees']} files={summary['files']} qres_files={summary['qres_files']}")
    print(
        f"typography_hits={summary['typography_hits']} "
        f"carved={summary.get('carved', 0)} slices={summary.get('slices', 0)}"
    )
    print(f"interesting: {summary['interesting_trees']}")
    if summary.get("failed_interesting"):
        print(f"failed: {summary['failed_interesting']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
