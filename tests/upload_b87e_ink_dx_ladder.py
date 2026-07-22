#!/usr/bin/env python3
"""Upload b87e page-wide ink DX ladder (− = left).

Fonts/S/L2dy locked. Shared DX on all styles.

  poetry run python tests/upload_b87e_ink_dx_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# current 0, then leftward
DXS = (0, -2, -4, -6, -8, -10)


def main() -> int:
    n = len(DXS)
    for i, dx in enumerate(DXS, 1):
        tag = f"b87e-inkDX-{i}of{n}-dx{dx:g}"
        title = f"{tag} (− left)"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--ink-dx",
            str(dx),
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
    print(f"done: {n} pages. Pick best inkDX Nof{n} (ink vs typed left edge).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
