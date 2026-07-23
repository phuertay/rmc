#!/usr/bin/env python3
"""Upload L3/L4 font size ladders at 0.5pt (OneNote max font precision).

Locked calib otherwise. Page ink scale stays INK_SCALE=1.55.

  poetry run python tests/upload_b87e_l34_font_ladder.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

BASE = [
    "--ink-dx", "-4",
    "--text-dx", "-60",
    "--text-dy", "-28",
    "--text-dy-l234", "30",
    "--text-dy-l34", "15",
    "--text-dy-l3", "5",
    "--text-dy-l4", "23",
    "--l1-text-dy", "-2",
    "--l2-text-dy", "8",
    "--heading", "32",
    "--bold", "23",
]

# 0.5pt steps around current 17.5 / 16
L3_SIZES = (16.5, 17.0, 17.5, 18.0, 18.5)
L4_SIZES = (15.0, 15.5, 16.0, 16.5, 17.0)


def _up(tag: str, title: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(UPLOAD), "--title", title, "--tag", tag, *BASE, *extra]
    print("===", title, "===")
    for attempt in range(1, 4):
        r = subprocess.run(cmd, cwd=str(ROOT.parent))
        if r.returncode == 0:
            time.sleep(1.5)
            return 0
        time.sleep(2 * attempt)
    return 1


def main() -> int:
    n3 = len(L3_SIZES)
    for i, b2 in enumerate(L3_SIZES, 1):
        tag = f"b87e-L3pt-{i}of{n3}-p{str(b2).replace('.', 'p')}"
        if _up(tag, f"{tag} L4=16", ["--second-bold", str(b2), "--plain", "16"]):
            return 1
    n4 = len(L4_SIZES)
    for i, p in enumerate(L4_SIZES, 1):
        tag = f"b87e-L4pt-{i}of{n4}-p{str(p).replace('.', 'p')}"
        if _up(tag, f"{tag} L3=17.5", ["--second-bold", "17.5", "--plain", str(p)]):
            return 1
    print(
        f"done: {n3} L3pt + {n4} L4pt pages (0.5pt steps). "
        "Pick L3pt Nof5 and L4pt Nof5. Ink page scale still S=1.55."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
