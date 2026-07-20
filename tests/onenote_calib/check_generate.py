"""Offline sanity check for the calib page generator (no Graph token)."""
from __future__ import annotations

from pathlib import Path

from generate_calib_page import generate
from rmc.exporters.inmkl import CSS_PER_HIMETRIC, inkml_to_css

OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    man = generate(OUT, title="rmc-calib-check")
    assert man["title"] == "rmc-calib-check"
    assert len(man["markers"]) == 4
    for m in man["markers"]:
        ix, iy = m["inkml"]
        nl, nt = m["css_new"]
        ol, ot = m["css_old_div10"]
        assert abs(nl - inkml_to_css(ix)) < 0.01
        assert abs(nt - inkml_to_css(iy)) < 0.01
        assert abs(ol - round(ix / 10)) < 0.01 and abs(ot - round(iy / 10)) < 0.01
        assert float(nl).is_integer() and float(nt).is_integer()
        # New CSS is much smaller than legacy ÷10 for these inkml values.
        assert nl < ol and nt < ot
    html = (OUT / "calib.html").read_text(encoding="utf-8")
    assert "<title>rmc-calib-check</title>" in html
    assert "NA" in html and "OA" in html
    # OneNote rejects fractional left/top — emitter must use integers.
    assert "left:346px" in html or "left:346.0px" not in html
    assert ".17px" not in html and ".93px" not in html
    assert man["cross_arm_himetric"] >= 400
    assert abs(man["css_per_himetric"] - CSS_PER_HIMETRIC) < 1e-12
    print("ok calib generate:", {"markers": 4, "out": str(OUT)})


if __name__ == "__main__":
    main()
