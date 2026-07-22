#!/usr/bin/env python3
"""Upload b87e VF font-size ladder (glyph proportions × scale).

Proportions from device PDF glyph heights (H:B1:B2:P ≈ 2.55:1.45:1.125:1).
Mid absolute = glyph_pt × INK_SCALE. Ladder varies one overall scale.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_font_ladder.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# Mid = glyph × INK_SCALE (see check_b87e_ink_font_scale / PDF carve)
MID = (30.98, 17.68, 13.67, 12.15)  # H, B1, B2, P
SCALES = (0.85, 0.925, 1.0, 1.075, 1.15)


def main() -> int:
    if not os.environ.get("ONENOTE_TOKEN") or not os.environ.get("ONENOTE_SECTION"):
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1
    n = len(SCALES)
    for i, k in enumerate(SCALES, 1):
        h, b, b2, p = (round(x * k, 2) for x in MID)
        tag = f"b87e-VF-glyph-{i}of{n}-k{str(k).replace('.', 'p')}"
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
    print(f"done: {n} pages (glyph ratios). Pick best Nof{n}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
