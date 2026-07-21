"""b87e: ink box vs HTML text left/top in exported InkML+HTML.

Catches pipeline drift (not OneNote font/chrome). Device/.rm already has
text≈box left; after left-edge scale, export CSS should stay within a few px.

Run: poetry run python tests/check_b87e_ink_text_align.py
"""
from __future__ import annotations

import re
import sys
from io import StringIO
from pathlib import Path

from rmscene import read_tree
from rmc.exporters import inmkl as ink

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"
# Local pipeline: ink vs HTML should hug. OneNote desktop may still need EXTRA nudge.
OK_DX = 6.0  # CSS px
OK_DY = 10.0


def _export(tree):
    xml, html = StringIO(), StringIO()
    # tree_to_html / tree_to_xml use output.name for title only
    xml.name = "b87e_align_check.xml"
    html.name = "b87e_align_check.html"
    ink.trace_id = 1
    ink.tree_to_xml(tree, xml)
    ink.tree_to_html(tree, html)
    return xml.getvalue(), html.getvalue()


def _html_divs(html: str):
    out = []
    for left, top, inner in re.findall(
        r"left:(\d+)px;top:(\d+)px[^>]*>(.*?)</div>", html, re.S
    ):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()
        if text:
            out.append((int(left), int(top), text))
    return out


def _ink_boxes_css(xml: str):
    """Large stroke bboxes in CSS px (himetric * 96/2540), Y-sorted."""
    boxes = []
    for t in re.findall(r"<inkml:trace[^>]*>([^<]+)</inkml:trace>", xml):
        pts = [p.split() for p in t.split(",") if p.strip()]
        xs = [int(p[0]) for p in pts]
        ys = [int(p[1]) for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        # INK_SCALE=1.5 can lift scrap strokes past a bare height floor.
        if h < 400 or w < 1000:
            continue
        boxes.append(
            (
                min(xs) * 96 / 2540,
                min(ys) * 96 / 2540,
                w * 96 / 2540,
                h * 96 / 2540,
            )
        )
    return sorted(boxes, key=lambda b: b[1])


def main() -> None:
    assert RM.is_file(), RM
    with RM.open("rb") as f:
        tree = read_tree(f)
    xml, html = _export(tree)
    divs = _html_divs(html)
    boxes = _ink_boxes_css(xml)
    assert len(divs) == len(boxes) == 4, (len(divs), len(boxes))

    print(
        f"INK_EXTRA_DX_CSS={ink.INK_EXTRA_DX_CSS} "
        f"INK_EXTRA_DY_CSS={ink.INK_EXTRA_DY_CSS} "
        f"PAGE_NUDGE_DY_CSS={ink.PAGE_NUDGE_DY_CSS}"
    )
    print("line                          dx     dy   inkL  htmlL  inkT  htmlT")
    bad = []
    for (hl, ht, text), (il, it, _w, _h) in zip(divs, boxes):
        dx, dy = il - hl, it - ht
        flag = ""
        if abs(dx) > OK_DX or abs(dy) > OK_DY:
            flag = " <--"
            bad.append(text[:24])
        print(
            f"{text[:28]:28} {dx:+6.1f} {dy:+6.1f} {il:6.1f} {hl:6d} {it:6.1f} {ht:6d}{flag}"
        )

    if bad:
        print(
            f"FAIL: |dx|>{OK_DX} or |dy|>{OK_DY} on {bad}. "
            "Tune INK_EXTRA_* (pipeline). Desktop OneNote may still differ."
        )
        sys.exit(1)
    print(
        f"ok: local ink↔HTML within ±{OK_DX}dx / ±{OK_DY}dy CSS. "
        "Desktop residual → live INK_EXTRA ladder / screenshot."
    )


if __name__ == "__main__":
    main()
