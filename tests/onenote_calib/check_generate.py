#!/usr/bin/env python3
"""Offline sanity check for the calib page generator (no Graph token)."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_calib_page import generate, OUT, TRUE_HIMETRIC_PER_CSS

man = generate()
assert (OUT / "calib.xml").is_file() and (OUT / "calib.html").is_file()
html = (OUT / "calib.html").read_text(encoding="utf-8")
xml = (OUT / "calib.xml").read_text(encoding="utf-8")
assert html.count("position: absolute") == 9  # 4*O + 4*H + legend
assert xml.count("<inkml:trace") >= 8 + 22  # 4 crosses *2 + rulers
for m in man["markers"]:
    ix, iy = m["inkml"]
    ol, ot = m["css_ours"]
    hl, ht = m["css_true_himetric"]
    assert abs(ol - ix / 10) < 0.01 and abs(ot - iy / 10) < 0.01
    assert abs(hl - ix / TRUE_HIMETRIC_PER_CSS) < 0.01
    # Hypotheses must disagree (otherwise the page teaches nothing).
    assert abs(ol - hl) > 20 or abs(ot - ht) > 20, m
print("ok calib generate:", json.dumps({"markers": len(man["markers"]), "out": str(OUT)}))
