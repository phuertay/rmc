"""b87e: uniform ink scale + locked L1/L2 VF fonts.

H/B1 locked from OneNote style-ladder picks; L3/L4 free (ladder).

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

LOCK_H, LOCK_B1 = 34.13, 24.1
OK = 0.02  # pt


def main() -> None:
    assert RM.is_file(), RM
    with RM.open("rb") as f:
        tree = read_tree(f)
    doc = TextDocument.from_scene_item(tree.root_text)
    lines = []
    bold_n = 0
    for p in doc.contents:
        if not str(p).strip():
            continue
        st = p.style.value
        bold_ord = 1
        if st == si.ParagraphStyle.BOLD:
            bold_n += 1
            bold_ord = bold_n
        pt = ink.rm_font_size_pt(st, bold_ordinal=bold_ord)
        S = ink.rm_ink_scale_for_style(st, bold_ordinal=bold_ord)
        lines.append((str(p).strip()[:28], pt, S, st, bold_ord))
    assert len(lines) == 4, lines
    print("line                          font_pt  ink_S")
    for label, pt, S, _st, _bo in lines:
        print(f"{label:28} {pt:7.2f}  {S:6.3f}")
    h, b1 = lines[0][1], lines[1][1]
    if abs(h - LOCK_H) > OK or abs(b1 - LOCK_B1) > OK:
        print(f"FAIL: H/B1 want {LOCK_H}/{LOCK_B1} got {h}/{b1}")
        sys.exit(1)
    if any(abs(S - ink.INK_SCALE) > 1e-6 for _l, _p, S, _st, _bo in lines):
        print("FAIL: ink scale must be page-wide")
        sys.exit(1)
    print(f"ok: H/B1 locked {h:g}/{b1:g}; L3/L4={lines[2][1]:g}/{lines[3][1]:g}; "
          f"INK_SCALE={ink.INK_SCALE}")


if __name__ == "__main__":
    main()
