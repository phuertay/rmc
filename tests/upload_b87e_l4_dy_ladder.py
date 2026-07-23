#!/usr/bin/env python3
"""Upload b87e L4-only text-down ladder.

Locked: inkDX-4, textDX-60, textDY-28, L234dy-30, L34dy-15.

  poetry run python tests/upload_b87e_l4_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

NUDGES = (0, 8, 12, 15, 20, 25)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L4dy-{i}of{n}-dy{dy:g}"
        title = f"{tag} (+ lowers L4 only)"
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
    print(f"done: {n} pages. Pick best L4dy Nof{n} (+ = lower L4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
