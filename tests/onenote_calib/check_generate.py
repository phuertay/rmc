"""Offline sanity check for the calib page generator (no Graph token)."""
from __future__ import annotations

from pathlib import Path

from generate_calib_page import generate
from rmc.exporters.inmkl import CSS_ALIGN_DX, CSS_ALIGN_DY, CSS_PER_HIMETRIC, PAGE_NUDGE_DY_CSS, inkml_to_css

OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    man = generate(OUT, title="rmc-calib-check")
    assert man["title"] == "rmc-calib-check"
    assert len(man["markers"]) == 4
    assert man["cross_arm_himetric"] >= 800
    for m in man["markers"]:
        ix, iy = m["inkml"]
        nl, nt = m["css_new"]
        ol, ot = m["css_old_div10"]
        assert abs(nl - (inkml_to_css(ix) + CSS_ALIGN_DX)) < 0.01
        assert abs(nt - (inkml_to_css(iy) + CSS_ALIGN_DY + PAGE_NUDGE_DY_CSS)) < 0.01
        assert abs(ol - round(ix / 10)) < 0.01 and abs(ot - round(iy / 10)) < 0.01
        assert float(nl).is_integer() and float(nt).is_integer()
        assert nl < ol and nt < ot
    html = (OUT / "calib.html").read_text(encoding="utf-8")
    assert "<title>rmc-calib-check</title>" in html
    assert ">+<" in html or ">+</p>" in html
    assert ".17px" not in html and ".93px" not in html
    assert abs(man["css_per_himetric"] - CSS_PER_HIMETRIC) < 1e-12
    xml = (OUT / "calib.xml").read_text(encoding="utf-8")
    assert xml.count("<inkml:trace") > 20  # arms + ticks + center fills
    print("ok calib generate:", {"markers": 4, "traces": xml.count("<inkml:trace"), "out": str(OUT)})


if __name__ == "__main__":
    main()
