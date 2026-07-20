"""Prove ink and typed text share one RM → InkML → CSS pipeline.

System under test (see inmkl module docstring):
  RM (bbox origin) → * RM_PER_INK + pad = InkML (himetric)
                   → * 96/2540           = HTML CSS px
  Text line Y = build_anchor_pos Y (same as ink group anchors).

Run: poetry run python tests/check_inkml_text_layout.py
"""
from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
import re

from rmscene import read_tree
from rmscene.scene_stream import simple_text_document, write_blocks
from rmscene.text import TextDocument
from rmc.exporters.inmkl import (
    CSS_PER_HIMETRIC,
    RM_PER_INK,
    inkml_to_css,
    rm_delta_to_css,
    rm_to_css,
    rm_to_inkml,
    set_page_origin,
    tree_to_html,
    tree_to_xml,
)
from rmc.exporters.svg import TEXT_TOP_Y, build_anchor_pos, get_bounding_box

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm"
FIXTURE = RM / "onenote_text_block.rm"
EXAMPLE_TEXT = "This is typed\n\n\n\n\n\n\nAnd this is typed again"


def _export(path: Path) -> tuple[str, str]:
    with path.open("rb") as f:
        tree = read_tree(f)
    xml_buf, html_buf = StringIO(), StringIO()
    xml_buf.name = path.stem + ".xml"
    html_buf.name = path.stem + ".html"
    tree_to_xml(tree, xml_buf)
    with path.open("rb") as f:
        tree = read_tree(f)
    tree_to_html(tree, html_buf)
    return xml_buf.getvalue(), html_buf.getvalue()


def _ink_css_y_range(xml: str) -> tuple[float, float] | None:
    ys = []
    for m in re.finditer(r"<inkml:trace[^>]*>([^<]+)</inkml:trace>", xml):
        for trip in m.group(1).split(","):
            parts = trip.split()
            if len(parts) >= 2:
                ys.append(inkml_to_css(int(parts[1])))
    if not ys:
        return None
    return min(ys), max(ys)


def _abs_tops(html: str) -> list[float]:
    return [float(t) for t in re.findall(r"top: ([0-9.]+)px", html)]


def ensure_fixture() -> Path:
    buf = BytesIO()
    write_blocks(buf, simple_text_document(EXAMPLE_TEXT))
    FIXTURE.write_bytes(buf.getvalue())
    return FIXTURE


def check_pipeline_identity() -> None:
    """Same RM point → CSS from rm_to_css equals CSS from InkML path."""
    set_page_origin((-702.0, 702.0, 0.0, 1872.0))
    for x, y in [(-468.0, 146.0), (-468.0, 216.0), (0.0, 500.0), (100.5, 999.25)]:
        ix, iy = rm_to_inkml(x, y)
        cx, cy = rm_to_css(x, y)
        assert abs(cx - inkml_to_css(ix)) < 1e-6 and abs(cy - inkml_to_css(iy)) < 1e-6, (
            x, y, ix, iy, cx, cy
        )
        # 1 RM → ~RM_PER_INK himetric (int trunc) → ~96/226 CSS px
        ix2, _ = rm_to_inkml(x + 1, y)
        assert abs((ix2 - ix) - RM_PER_INK) < 1.0
        assert abs(inkml_to_css(ix2) - inkml_to_css(ix) - rm_delta_to_css(1.0)) < CSS_PER_HIMETRIC
        assert abs(CSS_PER_HIMETRIC - 96 / 2540) < 1e-15


def check_text_y_matches_ink_anchors(path: Path) -> None:
    """HTML tops must use build_anchor_pos Y, not draw_text's +LINE_HEIGHT slot."""
    from rmc.exporters.svg import LINE_HEIGHTS

    with path.open("rb") as f:
        tree = read_tree(f)
    text = tree.root_text
    assert text is not None
    anchors = build_anchor_pos(text)
    set_page_origin(get_bounding_box(tree.root, anchors))
    doc = TextDocument.from_scene_item(text)
    _, html = _export(path)
    tops = [round(t, 2) for t in _abs_tops(html)]

    run_tops = []
    ypos = text.pos_y + TEXT_TOP_Y
    in_run = False
    for p in doc.contents:
        if str(p).strip():
            if not in_run:
                _l, top = rm_to_css(text.pos_x, ypos)
                run_tops.append(round(top, 2))
                in_run = True
        else:
            in_run = False
        ypos += LINE_HEIGHTS.get(p.style.value, 70)
    assert tops == run_tops, f"{path.name}: html tops {tops} != anchor-based {run_tops}"


def check_text_ink_text_fields(path: Path) -> None:
    _, html = _export(path)
    tops = _abs_tops(html)
    assert len(tops) >= 2, f"{path.name}: want ≥2 text fields, got {tops}\n{html}"
    assert tops == sorted(tops), tops
    # Gap is in CSS px after himetric scale (~0.42× RM).
    assert tops[-1] - tops[0] >= 20, tops
    assert "This is typed" in html and "And this is typed again" in html


def check_ink_text_same_origin(path: Path) -> None:
    """Ink traces and HTML tops must come from the same frozen RM origin + map."""
    with path.open("rb") as f:
        tree = read_tree(f)
    text = tree.root_text
    assert text is not None
    anchors = build_anchor_pos(text)
    set_page_origin(get_bounding_box(tree.root, anchors))
    xml, html = _export(path)
    tops = _abs_tops(html)
    assert tops, html
    from rmc.exporters.svg import LINE_HEIGHTS

    doc = TextDocument.from_scene_item(text)
    ypos = text.pos_y + TEXT_TOP_Y
    for p in doc.contents:
        if str(p).strip():
            _l, expect = rm_to_css(text.pos_x, ypos)
            assert abs(tops[0] - expect) < 0.6, (tops[0], expect)
            break
        ypos += LINE_HEIGHTS.get(p.style.value, 70)
    ink = _ink_css_y_range(xml)
    assert ink is not None
    assert ink[1] > ink[0] >= 0


def main() -> None:
    ensure_fixture()
    check_pipeline_identity()
    check_text_y_matches_ink_anchors(FIXTURE)
    check_text_y_matches_ink_anchors(RM / "text_and_strokes.rm")
    check_text_ink_text_fields(FIXTURE)
    check_ink_text_same_origin(RM / "text_and_strokes.rm")
    _, multi = _export(RM / "text_multiple_lines.rm")
    assert len(_abs_tops(multi)) >= 2, multi
    print("ok: unified RM→InkML→CSS + text Y == ink anchors")


if __name__ == "__main__":
    main()
