"""b87e: per-line ink-box vs glyph/font scale.

Device PDF outlines + .rm boxes. Uniform INK_SCALE cannot fit all four lines
(box/glyph ~1.28→1.72). Exporter must use per-style scales about each group.

Run: poetry run python tests/check_b87e_ink_font_scale.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader
from rmscene import read_tree, scene_items as si
from rmscene.text import TextDocument
from rmc.exporters import inmkl as ink
from rmc.exporters.svg import (
    LINE_HEIGHTS,
    TEXT_TOP_Y,
    build_anchor_pos,
    get_anchor,
)

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"
PDF_CANDIDATES = [
    Path("/home/ubuntu/.cursor/projects/workspace/uploads/the_pdf_41d6.pdf"),
    ROOT / "expected" / "b87e_device_render.pdf",
]
PT_PER_RM = 72 / 226
# Target: scaled box ≈ font (slight pad OK). Device title pad was ~1.28 pre-scale.
OK_LO, OK_HI = 1.00, 1.20


def _path_points(s: str):
    pts = []
    for m in re.finditer(
        r"([\d.\-eE]+)\s+([\d.\-eE]+)\s+m\b|"
        r"([\d.\-eE]+)\s+([\d.\-eE]+)\s+l\b|"
        r"(?:[\d.\-eE]+\s+){4}([\d.\-eE]+)\s+([\d.\-eE]+)\s+c\b",
        s,
    ):
        g = m.groups()
        if g[0] is not None:
            pts.append((float(g[0]), float(g[1])))
        elif g[2] is not None:
            pts.append((float(g[2]), float(g[3])))
        else:
            pts.append((float(g[4]), float(g[5])))
    return pts


def _glyph_heights_pt(pdf: Path) -> list[float]:
    raw = PdfReader(str(pdf)).pages[0].get_contents().get_data().decode("latin-1", errors="replace")
    out = []
    for seg in raw.split("1 0 0 1 234 234 cm")[1:5]:
        ys = [p[1] for p in _path_points(seg[:50000])]
        out.append((max(ys) - min(ys)) * PT_PER_RM)
    return out


def _ink_boxes(tree):
    anchors = build_anchor_pos(tree.root_text)
    out = []

    def walk(item, move=(0.0, 0.0)):
        for child in item.children.values():
            if isinstance(child, si.Group):
                ax, ay = get_anchor(child, anchors)
                walk(child, (move[0] + ax, move[1] + ay))
            elif isinstance(child, si.Line) and len(child.points) >= 2:
                xs = [pt.x + move[0] for pt in child.points]
                ys = [pt.y + move[1] for pt in child.points]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if w >= 40 and h >= 20:
                    out.append(h)

    walk(tree.root)
    return sorted(out, reverse=True)[:4]


def _typed_lines(tree):
    text = tree.root_text
    doc = TextDocument.from_scene_item(text)
    lines = []
    bold_n = 0
    for p in doc.contents:
        s = str(p).strip()
        if not s:
            continue
        st = p.style.value
        bold_ord = 1
        if st == si.ParagraphStyle.BOLD:
            bold_n += 1
            bold_ord = bold_n
        pt = ink.rm_font_size_pt(st, bold_ordinal=bold_ord)
        scale = ink.rm_ink_scale_for_style(st, bold_ordinal=bold_ord)
        lines.append((s, pt, scale, st, bold_ord))
    return lines


def main() -> None:
    pdf = next((p for p in PDF_CANDIDATES if p.is_file()), None)
    assert pdf is not None, f"missing device PDF; tried {PDF_CANDIDATES}"
    assert RM.is_file(), RM

    with RM.open("rb") as f:
        tree = read_tree(f)
    glyphs = _glyph_heights_pt(pdf)
    boxes_rm = _ink_boxes(tree)
    lines = _typed_lines(tree)
    assert len(glyphs) == len(boxes_rm) == len(lines) == 4

    print("line                          glyph  box_pt  ideal_S  S_used  box/font")
    bad = []
    scales = []
    for (label, font_pt, S, _st, _bo), g, h_rm in zip(lines, glyphs, boxes_rm):
        box_pt = h_rm * PT_PER_RM
        ideal = g / box_pt
        after = (box_pt * S) / font_pt
        scales.append(S)
        flag = "" if OK_LO <= after <= OK_HI else " <--"
        if flag:
            bad.append(label[:20])
        print(
            f"{label[:28]:28} {g:6.2f} {box_pt:7.2f} {ideal:8.2f} {S:7.3f} {after:8.2f}{flag}"
        )

    ideals = [g / (h * PT_PER_RM) for g, h in zip(glyphs, boxes_rm)]
    print(
        f"\nscales={scales}; ideal_S={[round(x, 2) for x in ideals]}; "
        f"uniform INK_SCALE={ink.INK_SCALE}"
    )
    if max(ideals) - min(ideals) > 0.1 and len(set(round(s, 3) for s in scales)) < 2:
        print("FAIL: ideal_S spread > 0.1 but exporter still uses one scale.")
        sys.exit(1)
    if bad:
        print(f"FAIL: box/font out of [{OK_LO},{OK_HI}] after per-line scale: {bad}")
        sys.exit(1)
    print("ok: per-line ink scales fit all lines")


if __name__ == "__main__":
    main()
