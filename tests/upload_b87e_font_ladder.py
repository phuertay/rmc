#!/usr/bin/env python3
"""Upload b87e VF font-size ladder (Style proportions × scale).

Proportions: Style map B 68:48:28 + B2=18/16×plain.
Mid H=33.3 (OneNote: L1 fit glyph-ladder #4); rest scaled from Style ratios.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_font_ladder.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# Mid: Style ratios, H from VF-glyph ladder #4 L1 fit
MID = (33.3, 23.51, 15.42, 13.71)  # H, B1, B2, P
SCALES = (0.90, 0.95, 1.0, 1.05, 1.10)


def main() -> int:
    if not os.environ.get("ONENOTE_TOKEN") or not os.environ.get("ONENOTE_SECTION"):
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1
    n = len(SCALES)
    for i, k in enumerate(SCALES, 1):
        h, b, b2, p = (round(x * k, 2) for x in MID)
        tag = f"b87e-VF-style-{i}of{n}-k{str(k).replace('.', 'p')}"
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
    print(f"done: {n} pages (Style ratios, mid H=33.3). Pick best Nof{n}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
