#!/usr/bin/env python3
"""Upload b87e INK_SCALE ladder (fonts locked at VF pick).

Fonts stay 34.13/24.1/19.12/17. Scale starts at current 1.5875 and goes up.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_ink_scale_ladder.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# locked VF fonts
H, B1, B2, P = 34.13, 24.1, 19.12, 17.0
# increase ink from current lock
SCALES = (1.5875, 1.70, 1.85, 2.00, 2.15, 2.30)


def main() -> int:
    if not os.environ.get("ONENOTE_TOKEN") or not os.environ.get("ONENOTE_SECTION"):
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1
    n = len(SCALES)
    for i, S in enumerate(SCALES, 1):
        stag = str(S).replace(".", "p")
        tag = f"b87e-VF-inkS-{i}of{n}-S{stag}"
        title = f"{tag} fonts {H:g}/{B1:g}/{B2:g}/{P:g}"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--ink-scale",
            str(S),
            "--heading",
            str(H),
            "--bold",
            str(B1),
            "--second-bold",
            str(B2),
            "--plain",
            str(P),
        ]
        print("===", title, "===")
        r = subprocess.run(cmd, cwd=str(ROOT.parent))
        if r.returncode != 0:
            return r.returncode
    print(f"done: {n} pages. Pick best ink scale Nof{n} (box vs typed text size).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
