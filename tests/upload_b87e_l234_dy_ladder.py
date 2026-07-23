#!/usr/bin/env python3
"""Upload b87e L2–L4 text-down ladder (+CSS px; ~one line = 30).

Locked: inkDX-4, textDX-60, textDY-28. L1 unchanged.

  poetry run python tests/upload_b87e_l234_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# + lowers L2–L4; ~30 = one BOLD LINE_HEIGHT in CSS
NUDGES = (0, 15, 25, 30, 35, 45)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L234dy-{i}of{n}-dy{dy:g}"
        title = f"{tag} (+ lowers L2-L4; ~30=1 line)"
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
    print(f"done: {n} pages. Pick best L234dy Nof{n} (+ = lower L2–L4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
