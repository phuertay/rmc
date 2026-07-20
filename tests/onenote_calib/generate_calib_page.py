#!/usr/bin/env python3
"""Build a OneNote calibration page (InkML + HTML) from known RM points.

The page is self-describing so a human (or screenshot) can see which CSS
hypothesis lands on the ink:

  - Ink: crosses at known RM corners (via our rm_to_inkml)
  - Letter O: HTML at our current mapping (inkml / RM_PER_INK)
  - Letter H: HTML at true-himetric CSS (inkml * 96/2540)

Whichever letter sits on the cross is the correct OneNote scale.
Also draws ink tick rulers (0..1000 RM) on X/Y for stretch checks.

Output (default tests/onenote_calib/out/):
  calib.xml  calib.html  manifest.json

Usage:
  poetry run python tests/onenote_calib/generate_calib_page.py
"""
from __future__ import annotations

import json
from pathlib import Path

from rmc.exporters.inmkl import (
    RM_PER_INK,
    X_PAD,
    Y_PAD,
    set_page_origin,
    rm_to_inkml,
    rm_to_css,
)
from rmc.exporters.svg import SCREEN_DPI

OUT = Path(__file__).resolve().parent / "out"
# Same default bbox as a blank RM page (matches get_bounding_box default).
BBOX = (-702.0, 702.0, 0.0, 1872.0)
# Square of known RM points (relative to bbox origin → easy mental math).
CORNERS_RM = [
    (0.0, 200.0, "A"),
    (400.0, 200.0, "B"),
    (0.0, 600.0, "C"),
    (400.0, 600.0, "D"),
]
TRUE_HIMETRIC_PER_CSS = 2540 / 96
RM_TO_TRUE_HIMETRIC = 2540 / SCREEN_DPI


def _cross_inkml(cx: int, cy: int, arm: int = 80) -> str:
    """Two short traces forming a + at (cx,cy) himetric."""
    h = [
        f"{cx - arm} {cy} 64",
        f"{cx} {cy} 96",
        f"{cx + arm} {cy} 64",
    ]
    v = [
        f"{cx} {cy - arm} 64",
        f"{cx} {cy} 96",
        f"{cx} {cy + arm} 64",
    ]
    return ",".join(h), ",".join(v)


def _tick_traces(axis: str) -> list[str]:
    """Ruler ticks every 100 RM from 0..1000."""
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


def generate(out_dir: Path = OUT) -> dict:
    set_page_origin(BBOX)
    out_dir.mkdir(parents=True, exist_ok=True)

    traces: list[str] = []
    markers: list[dict] = []

    for rm_x, rm_y, label in CORNERS_RM:
        ix, iy = rm_to_inkml(rm_x, rm_y)
        our_l, our_t = rm_to_css(rm_x, rm_y)
        # True-himetric CSS for the same inkml point OneNote would compute at 96 DPI.
        true_l = ix / TRUE_HIMETRIC_PER_CSS
        true_t = iy / TRUE_HIMETRIC_PER_CSS
        h, v = _cross_inkml(ix, iy)
        traces.extend([h, v])
        markers.append(
            {
                "label": label,
                "rm": [rm_x, rm_y],
                "inkml": [ix, iy],
                "css_ours": [our_l, our_t],
                "css_true_himetric": [true_l, true_t],
            }
        )

    traces.extend(_tick_traces("x"))
    traces.extend(_tick_traces("y"))

    brush = """
    <inkml:brush xml:id="calib_pen">
        <inkml:brushProperty name="width" value="30" units="himetric" />
        <inkml:brushProperty name="height" value="30" units="himetric" />
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

    # HTML: O = our mapping, H = true-himetric mapping. Same ink cross for both.
    divs = []
    for m in markers:
        lab = m["label"]
        ol, ot = m["css_ours"]
        hl, ht = m["css_true_himetric"]
        divs.append(
            f'<div style="position: absolute; left: {ol:.2f}px; top: {ot:.2f}px; '
            f'font-size: 18pt; font-weight: bold; color: #c00">O{lab}</div>'
        )
        divs.append(
            f'<div style="position: absolute; left: {hl:.2f}px; top: {ht:.2f}px; '
            f'font-size: 18pt; font-weight: bold; color: #06c">H{lab}</div>'
        )
    divs.append(
        '<div style="position: absolute; left: 48px; top: 40px; width: 520px; '
        'font-family: Calibri; font-size: 11pt">'
        "<b>rmc OneNote calib</b><br/>"
        "Ink crosses = RM truth.<br/>"
        "<span style='color:#c00'>O*</span> = our CSS (inkml/10).<br/>"
        "<span style='color:#06c'>H*</span> = true-himetric CSS (inkml×96/2540).<br/>"
        "Whichever letter sits on the cross is the correct scale."
        "</div>"
    )
    html = f"""<html>
<head><title>rmc-onenote-calib</title></head>
<body data-absolute-enabled="true" style="font-family:Calibri;font-size:11pt">
{"".join(divs)}
</body>
</html>
"""
    html_path = out_dir / "calib.html"
    html_path.write_text(html, encoding="utf-8")

    manifest = {
        "bbox_rm": BBOX,
        "rm_per_ink": RM_PER_INK,
        "pad_inkml": [X_PAD, Y_PAD],
        "true_himetric_per_css_px": TRUE_HIMETRIC_PER_CSS,
        "rm_to_true_himetric": RM_TO_TRUE_HIMETRIC,
        "screen_dpi": SCREEN_DPI,
        "markers": markers,
        "how_to_read": (
            "Open the OneNote page. For each corner A–D, see whether the red O "
            "or the blue H sits on the ink cross. That picks the CSS scale."
        ),
        "files": {"xml": str(xml_path), "html": str(html_path)},
    }
    man_path = out_dir / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {xml_path}")
    print(f"wrote {html_path}")
    print(f"wrote {man_path}")
    return manifest


if __name__ == "__main__":
    generate()
