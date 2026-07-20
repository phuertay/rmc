#!/usr/bin/env python3
"""Build a OneNote calibration page (InkML + HTML) from known RM points.

After the true-himetric fix, ink and HTML share one pipeline. This page checks
that the new CSS lands on the ink, and shows where the old ÷10 CSS would sit:

  - Ink: large crosses at known RM corners (current rm_to_inkml)
  - Letter N: HTML at current rm_to_css (should sit on the cross)
  - Letter O: HTML at legacy ÷10 mapping of the same inkml (should miss)

Also draws ink tick rulers (0..1000 RM) on X/Y for stretch checks.

Output (default tests/onenote_calib/out/):
  calib.xml  calib.html  manifest.json

Usage:
  poetry run python tests/onenote_calib/generate_calib_page.py
  poetry run python tests/onenote_calib/generate_calib_page.py --title rmc-calib-20260720-195746
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rmc.exporters.inmkl import (
    CSS_PER_HIMETRIC,
    RM_PER_INK,
    X_PAD,
    Y_PAD,
    inkml_to_css,
    set_page_origin,
    rm_to_inkml,
    rm_to_css,
)
from rmc.exporters.svg import SCREEN_DPI

OUT = Path(__file__).resolve().parent / "out"
BBOX = (-702.0, 702.0, 0.0, 1872.0)
CORNERS_RM = [
    (0.0, 200.0, "A"),
    (400.0, 200.0, "B"),
    (0.0, 600.0, "C"),
    (400.0, 600.0, "D"),
]
# ~0.2 inch arms so crosses are obvious in OneNote / PDF.
CROSS_ARM_HIMETRIC = 500
TRUE_HIMETRIC_PER_CSS = 1 / CSS_PER_HIMETRIC


def _cross_inkml(cx: int, cy: int, arm: int = CROSS_ARM_HIMETRIC) -> tuple[str, str]:
    h = [f"{cx - arm} {cy} 64", f"{cx} {cy} 96", f"{cx + arm} {cy} 64"]
    v = [f"{cx} {cy - arm} 64", f"{cx} {cy} 96", f"{cx} {cy + arm} 64"]
    return ",".join(h), ",".join(v)


def _tick_traces(axis: str) -> list[str]:
    traces = []
    for i in range(0, 1001, 100):
        if axis == "x":
            x0, y0 = rm_to_inkml(float(i), 100.0)
            x1, y1 = rm_to_inkml(float(i), 100.0 + (40 if i % 500 == 0 else 20))
        else:
            x0, y0 = rm_to_inkml(50.0, float(i))
            x1, y1 = rm_to_inkml(50.0 + (40 if i % 500 == 0 else 20), float(i))
        traces.append(f"{x0} {y0} 48,{x1} {y1} 48")
    return traces


def generate(out_dir: Path = OUT, title: str | None = None) -> dict:
    set_page_origin(BBOX)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not title:
        title = "rmc-calib-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    traces: list[str] = []
    markers: list[dict] = []

    for rm_x, rm_y, label in CORNERS_RM:
        ix, iy = rm_to_inkml(rm_x, rm_y)
        new_l, new_t = rm_to_css(rm_x, rm_y)
        # Legacy cancel-CONV CSS (inkml/10) — wrong for OneNote, kept for contrast.
        old_l, old_t = float(round(ix / 10.0)), float(round(iy / 10.0))
        h, v = _cross_inkml(ix, iy)
        traces.extend([h, v])
        markers.append(
            {
                "label": label,
                "rm": [rm_x, rm_y],
                "inkml": [ix, iy],
                "css_new": [new_l, new_t],
                "css_old_div10": [old_l, old_t],
            }
        )

    traces.extend(_tick_traces("x"))
    traces.extend(_tick_traces("y"))

    brush = """
    <inkml:brush xml:id="calib_pen">
        <inkml:brushProperty name="width" value="60" units="himetric" />
        <inkml:brushProperty name="height" value="60" units="himetric" />
        <inkml:brushProperty name="color" value="#000000" />
        <inkml:brushProperty name="transparency" value="0" />
        <inkml:brushProperty name="tip" value="ellipse" />
        <inkml:brushProperty name="rasterOp" value="copyPen" />
        <inkml:brushProperty name="ignorePressure" value="true" />
        <inkml:brushProperty name="antiAliased" value="true" />
        <inkml:brushProperty name="fitToCurve" value="false" />
    </inkml:brush>"""

    xml_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<inkml:ink xmlns:emma="http://www.w3.org/2003/04/emma" '
        'xmlns:msink="http://schemas.microsoft.com/ink/2010/main" '
        'xmlns:inkml="http://www.w3.org/2003/InkML">',
        "  <inkml:definitions>",
        """    <inkml:context xml:id="ctxCoordinatesWithPressure">
        <inkml:inkSource xml:id="inkSrcCoordinatesWithPressure">
            <inkml:traceFormat>
                <inkml:channel name="X" type="integer" max="32767" units="himetric" />
                <inkml:channel name="Y" type="integer" max="32767" units="himetric" />
                <inkml:channel name="F" type="integer" max="32767" units="dev" />
            </inkml:traceFormat>
            <inkml:channelProperties>
                <inkml:channelProperty channel="X" name="resolution" value="1" units="1/himetric" />
                <inkml:channelProperty channel="Y" name="resolution" value="1" units="1/himetric" />
                <inkml:channelProperty channel="F" name="resolution" value="1" units="1/dev" />
            </inkml:channelProperties>
        </inkml:inkSource>
    </inkml:context>""",
        brush,
        "  </inkml:definitions>",
        "  <inkml:traceGroup>",
    ]
    for i, t in enumerate(traces, 1):
        xml_parts.append(
            f'    <inkml:trace xml:id="{i}" contextRef="#ctxCoordinatesWithPressure" '
            f'brushRef="#calib_pen">{t}</inkml:trace>'
        )
    xml_parts += ["  </inkml:traceGroup>", "</inkml:ink>", ""]
    xml_path = out_dir / "calib.xml"
    xml_path.write_text("\n".join(xml_parts), encoding="utf-8")

    divs = []
    for m in markers:
        lab = m["label"]
        nl, nt = m["css_new"]
        ol, ot = m["css_old_div10"]
        divs.append(
            f'<div style="position:absolute;left:{nl:.0f}px;top:{nt:.0f}px;width:80px">'
            f'<p style="margin:0;font-size:28pt;font-weight:bold;color:#00aa00">N{lab}</p></div>'
        )
        divs.append(
            f'<div style="position:absolute;left:{ol:.0f}px;top:{ot:.0f}px;width:80px">'
            f'<p style="margin:0;font-size:28pt;font-weight:bold;color:#cc0000">O{lab}</p></div>'
        )
    divs.append(
        '<div style="position:absolute;left:48px;top:40px;width:560px">'
        '<p style="margin:0;font-family:Calibri;font-size:11pt">'
        f"<b>{title}</b><br/>"
        "Judge in OneNote (not PDF). Fractional CSS left/top was zeroed by Graph — now integers.<br/>"
        "Ink crosses = RM truth.<br/>"
        "<span style='color:#00aa00'>N*</span> = new CSS (inkml*96/2540) — should sit on cross.<br/>"
        "<span style='color:#cc0000'>O*</span> = old CSS (inkml/10) — should miss."
        "</p></div>"
    )
    html = f"""<html>
<head><title>{title}</title></head>
<body data-absolute-enabled="true" style="font-family:Calibri;font-size:11pt">
{"".join(divs)}
</body>
</html>
"""
    html_path = out_dir / "calib.html"
    html_path.write_text(html, encoding="utf-8")

    manifest = {
        "title": title,
        "bbox_rm": BBOX,
        "rm_per_ink": RM_PER_INK,
        "pad_inkml": [X_PAD, Y_PAD],
        "css_per_himetric": CSS_PER_HIMETRIC,
        "true_himetric_per_css_px": TRUE_HIMETRIC_PER_CSS,
        "screen_dpi": SCREEN_DPI,
        "cross_arm_himetric": CROSS_ARM_HIMETRIC,
        "markers": markers,
        "how_to_read": (
            "N* (green) should sit on each ink cross. O* (red) is legacy ÷10 and should miss."
        ),
        "files": {"xml": str(xml_path), "html": str(html_path)},
    }
    man_path = out_dir / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {xml_path}")
    print(f"wrote {html_path}")
    print(f"wrote {man_path}")
    print(f"title: {title}")
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--title", default="", help="OneNote page title (default: rmc-calib-<UTC>)")
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args()
    generate(args.out, title=args.title or None)
