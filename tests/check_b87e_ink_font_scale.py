"""b87e: uniform ink scale + Style-ratio fonts (VF recalib).

Ink is one page-wide INK_SCALE. Font proportions follow Style map B
(68:48:28) with mid H from OneNote L1 fit; absolute scale is free.

Run: poetry run python tests/check_b87e_ink_font_scale.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from rmscene import read_tree, scene_items as si
from rmscene.text import TextDocument
from rmc.exporters import inmkl as ink

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"

# Style title.xl : title.lg : body.md
STYLE_H_OVER_P = 68 / 28
STYLE_B_OVER_P = 48 / 28
STYLE_B2_OVER_P = 18 / 16
OK_LO, OK_HI = 0.97, 1.03


def _typed_fonts(tree):
    doc = TextDocument.from_scene_item(tree.root_text)
    out = []
    bold_n = 0
    for p in doc.contents:
        if not str(p).strip():
            continue
        st = p.style.value
        bold_ord = 1
        if st == si.ParagraphStyle.BOLD:
            bold_n += 1
            bold_ord = bold_n
        out.append((str(p).strip()[:28], ink.rm_font_size_pt(st, bold_ordinal=bold_ord),
                    ink.rm_ink_scale_for_style(st, bold_ordinal=bold_ord)))
    return out


def main() -> None:
    assert RM.is_file(), RM
    with RM.open("rb") as f:
        tree = read_tree(f)
    lines = _typed_fonts(tree)
    assert len(lines) == 4, lines
    _h, b1, b2, p = (pt for _s, pt, _S in lines)
    print("line                          font_pt  /plain   ink_S")
    for label, pt, S in lines:
        print(f"{label:28} {pt:7.2f}  {pt/p:6.3f}  {S:6.3f}")
    print(f"\nwant H/P≈{STYLE_H_OVER_P:.3f} B1/P≈{STYLE_B_OVER_P:.3f} B2/P≈{STYLE_B2_OVER_P:.3f}")
    ratios = (_h / p, b1 / p, b2 / p)
    wants = (STYLE_H_OVER_P, STYLE_B_OVER_P, STYLE_B2_OVER_P)
    bad = []
    for name, got, want in zip(("H", "B1", "B2"), ratios, wants):
        r = got / want
        flag = "" if OK_LO <= r <= OK_HI else " <--"
        if flag:
            bad.append(name)
        print(f"  {name}/P got={got:.3f} want={want:.3f} got/want={r:.3f}{flag}")
    scales = [S for _s, _pt, S in lines]
    if any(abs(s - ink.INK_SCALE) > 1e-6 for s in scales):
        print("FAIL: ink scale must be page-wide")
        sys.exit(1)
    if bad:
        print(f"FAIL: Style ratio drift: {bad}")
        sys.exit(1)
    print(f"ok: Style ratios; INK_SCALE={ink.INK_SCALE}; mid fonts H/B1/B2/P="
          f"{_h:g}/{b1:g}/{b2:g}/{p:g}")


if __name__ == "__main__":
    main()
