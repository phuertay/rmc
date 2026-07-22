#!/usr/bin/env python3
"""Upload slight L1+L4 text-down ladder (same extra DY on both).

Locked base: inkDX-4, textDX-60, textDY-28, L234=30, L34=15, L4=25.
Ladder adds +d to L1 (HEADING) and +d more to L4 (on top of 25).

  poetry run python tests/upload_b87e_l1_l4_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# slight down for L1 and L4
NUDGES = (0, 4, 6, 8, 10, 12)


def main() -> int:
    n = len(NUDGES)
    for i, d in enumerate(NUDGES, 1):
        tag = f"b87e-L1L4dy-{i}of{n}-dy{d:g}"
        title = f"{tag} (+ lowers L1 & L4 slightly)"
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
            "--l1-text-dy",
            str(d),
            "--text-dy-l4",
            str(25 + d),
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
    print(f"done: {n} pages. Pick best L1L4dy Nof{n} (+ = lower L1 & L4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
