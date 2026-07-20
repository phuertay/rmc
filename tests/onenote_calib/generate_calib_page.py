#!/usr/bin/env python3
"""Build a OneNote calibration page (InkML + HTML) from known RM points.

Precision page for measuring residual HTML vs ink offset:

  - Ink: thin cross + filled center square + 1/4-arm ticks (unambiguous center)
  - Green "+": HTML at current rm_to_css (integer px). Top-left of the "+"
    glyph box is the CSS point; judge where the "+" intersection sits vs ink center.
  - Red "x": legacy inkml/10 (should miss)

Report e.g. "A: + center is 1/4 arm right, 1/8 arm down from ink square".

Usage:
  poetry run python tests/onenote_calib/generate_calib_page.py
  poetry run python tests/onenote_calib/generate_calib_page.py --title rmc-calib-…
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rmc.exporters.inmkl import (
    CSS_ALIGN_DX,
    CSS_ALIGN_DY,
    CSS_PER_HIMETRIC,
    RM_PER_INK,
    X_PAD,
    Y_PAD,
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
# ~0.4 inch arms; quarter ticks easy to read.
CROSS_ARM_HIMETRIC = 1000
CENTER_HALF_HIMETRIC = 40  # filled square ±40 himetric (~1.5 CSS px)
TRUE_HIMETRIC_PER_CSS = 1 / CSS_PER_HIMETRIC


def _trace_line(x0: int, y0: int, x1: int, y1: int, f: int = 80) -> str:
    return f"{x0} {y0} {f},{x1} {y1} {f}"


def _cross_traces(cx: int, cy: int, arm: int = CROSS_ARM_HIMETRIC) -> list[str]:
    """Thin + arms, quarter ticks, and a small filled center square."""
    traces = [
        _trace_line(cx - arm, cy, cx + arm, cy, 96),
        _trace_line(cx, cy - arm, cx, cy + arm, 96),
    ]
    # Quarter / half ticks on each arm (perpendicular hash marks).
    tick = max(arm // 10, 30)
    for d in (arm // 4, arm // 2, 3 * arm // 4):
        for sx, sy in ((-d, 0), (d, 0), (0, -d), (0, d)):
            if sx:
                traces.append(_trace_line(cx + sx, cy - tick, cx + sx, cy + tick, 64))
            else:
                traces.append(_trace_line(cx - tick, cy + sy, cx + tick, cy + sy, 64))
    # Filled center square (several strokes) = exact RM point.
    h = CENTER_HALF_HIMETRIC
    for dy in range(-h, h + 1, max(h // 4, 1)):
        traces.append(_trace_line(cx - h, cy + dy, cx + h, cy + dy, 120))
    return traces


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
        old_l, old_t = float(round(ix / 10.0)), float(round(iy / 10.0))
        traces.extend(_cross_traces(ix, iy))
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
        <inkml:brushProperty name="width" value="35" units="himetric" />
        <inkml:brushProperty name="height" value="35" units="himetric" />
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

    # "+" top-left = CSS point. Small label offset so it does not cover the center.
    divs = []
    for m in markers:
        lab = m["label"]
        nl, nt = m["css_new"]
        ol, ot = m["css_old_div10"]
        divs.append(
            f'<div style="position:absolute;left:{nl:.0f}px;top:{nt:.0f}px;width:40px">'
            f'<p style="margin:0;line-height:1;font-size:22pt;font-weight:bold;'
            f'color:#00aa00">+</p></div>'
        )
        divs.append(
            f'<div style="position:absolute;left:{nl + 22:.0f}px;top:{nt:.0f}px;width:30px">'
            f'<p style="margin:0;font-size:11pt;color:#00aa00">{lab}</p></div>'
        )
        divs.append(
            f'<div style="position:absolute;left:{ol:.0f}px;top:{ot:.0f}px;width:40px">'
            f'<p style="margin:0;line-height:1;font-size:22pt;font-weight:bold;'
            f'color:#cc0000">x</p></div>'
        )
    divs.append(
        '<div style="position:absolute;left:48px;top:40px;width:580px">'
        '<p style="margin:0;font-family:Calibri;font-size:11pt">'
        f"<b>{title}</b><br/>"
        "Ink: thin cross, quarter ticks, filled center square = exact point.<br/>"
        "<span style='color:#00aa00'>Green +</span> = new CSS + measured nudge "
        f"({CSS_ALIGN_DX:+d},{CSS_ALIGN_DY:+d})px. "
        "Label A–D is only a name tag.<br/>"
        "<span style='color:#cc0000'>Red x</span> = old CSS (inkml/10), should miss.<br/>"
        "<b>Expect:</b> green + intersection on the ink center square."
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
        "center_half_himetric": CENTER_HALF_HIMETRIC,
        "markers": markers,
        "how_to_read": (
            "Report green + intersection vs ink center square in arm fractions "
            "(quarter ticks on each arm)."
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
