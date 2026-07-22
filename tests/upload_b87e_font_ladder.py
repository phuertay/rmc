#!/usr/bin/env python3
"""Upload b87e VF L3/L4 font ladder (H/B1 locked).

L1/L2 from style-ladder #3–#4 mid (34.13 / 24.1).
L3/L4 plain ladder above prior style #5; B2 = 18/16 × plain.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_font_ladder.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

H, B1 = 34.13, 24.1
B2_OVER_P = 18 / 16
PLAINS = (16.0, 17.0, 18.0, 19.0, 20.0, 21.0)


def main() -> int:
    # upload_b87e_onenote.py loads /tmp/onenote_token.env if env empty
    n = len(PLAINS)
    for i, p in enumerate(PLAINS, 1):
        b2 = round(B2_OVER_P * p, 2)
        tag = f"b87e-VF-L34-{i}of{n}-p{str(p).replace('.', 'p')}"
        title = f"{tag} {H:g}/{B1:g}/{b2:g}/{p:g}"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--heading",
            str(H),
            "--bold",
            str(B1),
            "--second-bold",
            str(b2),
            "--plain",
            str(p),
        ]
        print("===", title, "===")
        r = subprocess.run(cmd, cwd=str(ROOT.parent))
        if r.returncode != 0:
            return r.returncode
    print(f"done: {n} pages (H/B1 locked). Pick best L3/L4 Nof{n}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
