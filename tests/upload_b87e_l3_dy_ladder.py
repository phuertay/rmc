#!/usr/bin/env python3
"""Upload fine L3 text-down ladder (1 CSS px steps @ 17.5pt).

  poetry run python tests/upload_b87e_l3_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# 1 CSS px steps (HTML tops are integers)
NUDGES = (0, 1, 2, 3, 4, 5, 6, 7, 8)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L3fine-{i}of{n}-dy{dy:g}"
        title = f"{tag} font17.5 (+ lowers L3, 1px)"
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
            "8",
            "--second-bold",
            "17.5",
            "--text-dy-l3",
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
    print(f"done: {n} pages. Pick best L3fine Nof{n} (+ = lower L3, 1 CSS px).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
