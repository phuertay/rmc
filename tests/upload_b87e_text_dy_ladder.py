#!/usr/bin/env python3
"""Upload b87e text-up ladder (HTML top −CSS px; DX locked −60).

~L1 "s" x-height ≈ 22 CSS @ 32pt.

  poetry run python tests/upload_b87e_text_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# 0 = current; negative = up
NUDGES = (0, -12, -17, -22, -28, -34)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-textDY-{i}of{n}-dy{dy:g}"
        title = f"{tag} DX-60 (− up)"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--text-dx",
            "-60",
            "--text-dy",
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
    print(f"done: {n} pages. Pick best textDY Nof{n} (− = up; ~22 ≈ L1 s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
