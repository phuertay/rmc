#!/usr/bin/env python3
"""Upload b87e L1 text-down ladder (HEADING HTML top +CSS px).

  poetry run python tests/upload_b87e_l1_text_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

NUDGES = (0, 2, 4, 6, 8)


def main() -> int:
    n = len(NUDGES)
    for i, dy in enumerate(NUDGES, 1):
        tag = f"b87e-L1dy-{i}of{n}-dy{dy:g}"
        title = f"{tag} (+ lowers L1 text)"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--l1-text-dy",
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
    print(f"done: {n} pages. Pick best L1dy Nof{n}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
