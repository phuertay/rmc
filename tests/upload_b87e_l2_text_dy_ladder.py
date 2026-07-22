#!/usr/bin/env python3
"""Upload b87e L2 text-down ladder (first BOLD HTML top +CSS px).

Fonts/S locked. +dy lowers L2 typed text vs ink.

  poetry run python tests/upload_b87e_l2_text_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# slight down from current (0)
NUDGES = (0, 2, 4, 6, 8)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L2dy-{i}of{n}-dy{dy:g}"
        title = f"{tag} (+ lowers L2 text)"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--l2-text-dy",
            str(dy),
        ]
        print("===", title, "===")
        for attempt in range(1, 4):
            r = subprocess.run(cmd, cwd=str(ROOT.parent))
            if r.returncode == 0:
                break
            if attempt == 3:
                return r.returncode
            time.sleep(2 * attempt)
        time.sleep(1.5)
    print(f"done: {n} pages. Pick best L2dy Nof{n} (L2 text vs ink box).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
