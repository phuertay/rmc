#!/usr/bin/env python3
"""Upload fine L1+L4 text-up ladder (−CSS px; same extra on both).

Locked base: inkDX-4, textDX-60, textDY-28, L234=30, L34=15, L4=25.
Ladder adds d (≤0) to L1 and to L4 (L4 = 25+d).

  poetry run python tests/upload_b87e_l1_l4_dy_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# finer up (−)
NUDGES = (0, -2, -4, -6, -8, -10)


def main() -> int:
    n = len(NUDGES)
    for i, d in enumerate(NUDGES, 1):
        tag = f"b87e-L1L4up-{i}of{n}-dy{d:g}"
        title = f"{tag} (− raises L1 & L4 fine)"
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
    print(f"done: {n} pages. Pick best L1L4up Nof{n} (− = text up).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
