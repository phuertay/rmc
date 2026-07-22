#!/usr/bin/env python3
"""Upload b87e VF font-size ladder to OneNote (INK_SCALE locked).

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_font_ladder.py

Keeps Style map B ratios (68:48:28) + BOLD#2 = 18/16 of plain.
Default mid = current 16pt plain. Pick best rung; tell agent Nof5.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# plain pt bases → H/B/B2/P via locked ratios
PLAIN_LADDER = (11.0, 13.0, 15.0, 16.0, 18.0, 20.0)
H_OVER_P = 68 / 28
B_OVER_P = 48 / 28
B2_OVER_P = 18 / 16


def sizes(plain: float) -> tuple[float, float, float, float]:
    h = round(H_OVER_P * plain, 2)
    b = round(B_OVER_P * plain, 2)
    b2 = round(B2_OVER_P * plain, 2)
    return h, b, b2, plain


def main() -> int:
    if not os.environ.get("ONENOTE_TOKEN") or not os.environ.get("ONENOTE_SECTION"):
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1
    n = len(PLAIN_LADDER)
    for i, plain in enumerate(PLAIN_LADDER, 1):
        h, b, b2, p = sizes(plain)
        tag = f"b87e-VF-fonts-{i}of{n}-p{str(p).replace('.', 'p')}"
        title = f"{tag} {h:g}/{b:g}/{b2:g}/{p:g}"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--heading",
            str(h),
            "--bold",
            str(b),
            "--second-bold",
            str(b2),
            "--plain",
            str(p),
        ]
        print("===", title, "===")
        r = subprocess.run(cmd, cwd=str(ROOT.parent))
        if r.returncode != 0:
            return r.returncode
    print(f"done: {n} pages. Pick best Nof{n} (text vs ink box size).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
