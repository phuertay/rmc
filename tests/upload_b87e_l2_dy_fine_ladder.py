#!/usr/bin/env python3
"""Upload fine L2 text-down ladder (+CSS px on first-BOLD nudge).

Locked: inkDX-4, textDX-60, textDY-28, L234=30, L34=15, L4=23, L1=-2.

  poetry run python tests/upload_b87e_l2_dy_fine_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# current BOLD1=6; finer down (+)
NUDGES = (6, 8, 10, 12, 14, 16)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L2down-{i}of{n}-dy{dy:g}"
        title = f"{tag} (+ lowers L2 fine)"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--ink-dx",
            "-4",
            "--text-dx",
            "-60",
            "--text-dy",
            "-28",
            "--text-dy-l234",
            "30",
            "--text-dy-l34",
            "15",
            "--text-dy-l4",
            "23",
            "--l1-text-dy",
            "-2",
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
    print(f"done: {n} pages. Pick best L2down Nof{n} (+ = lower L2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
