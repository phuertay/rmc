#!/usr/bin/env python3
"""Upload b87e INK_SCALE ladder (fonts locked; ink too large → step down).

Fonts stay 32/24/18.5/16. Coarse S from current lock downward.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_ink_scale_ladder.py

Ink coords are int himetric → effective size step ~0.001–0.002 in S
(1 himetric on glyph height). Eye ladders use ~0.05–0.1 coarse / ~0.01 fine.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / "upload_b87e_onenote.py"

# locked after H32-inkS-2of6 + L2→23
H, B1, B2, P = 32.0, 23.0, 18.5, 16.0
# current lock first, then smaller (ink too large)
SCALES = (1.55, 1.45, 1.35, 1.25, 1.15)


def main() -> int:
    if not os.environ.get("ONENOTE_TOKEN") or not os.environ.get("ONENOTE_SECTION"):
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1
    n = len(SCALES)
    for i, S in enumerate(SCALES, 1):
        stag = str(S).replace(".", "p")
        tag = f"b87e-H32-inkS-{i}of{n}-S{stag}"
        title = f"{tag} fonts {H:g}/{B1:g}/{B2:g}/{P:g}"
        cmd = [
            sys.executable,
            str(UPLOAD),
            "--title",
            title,
            "--tag",
            tag,
            "--ink-scale",
            str(S),
            "--heading",
            str(H),
            "--bold",
            str(B1),
            "--second-bold",
            str(B2),
            "--plain",
            str(P),
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
    print(f"done: {n} pages. Pick best ink scale Nof{n} (box vs typed text size).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
