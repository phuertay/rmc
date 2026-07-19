"""OneNote InkML/HTML layout checks + fixtures.

Example page pattern (from user OneNote export): typed → handwriting → typed.
Blank lines between typed runs must become separate absolute fields so ink can
sit in the gap (one big flowing div stacks all text and leaves no hole for ink).

Fixtures:
  tests/rm/text_and_strokes.rm     — ink + one typed word (overlap)
  tests/rm/onenote_text_block.rm   — typed / blank / typed (two fields)
  tests/rm/text_multiple_lines.rm  — blanks between runs

Run: poetry run python tests/check_inkml_text_layout.py
"""
from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
import re

from rmscene import read_tree
from rmscene.scene_stream import simple_text_document, write_blocks
from rmc.exporters.inmkl import HIMETRIC_PER_CSS_PX, tree_to_html, tree_to_xml

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm"
# Matches user Example.one: "This is typed" … ink gap … "And this is typed again"
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
                ys.append(int(parts[1]) / HIMETRIC_PER_CSS_PX)
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


def check_text_ink_text_fields(path: Path) -> None:
    """Typed runs separated by blanks → 2+ absolute fields, increasing tops."""
    _, html = _export(path)
    tops = _abs_tops(html)
    assert len(tops) >= 2, f"{path.name}: want ≥2 text fields for text/ink/text, got {tops}\n{html}"
    assert tops == sorted(tops), tops
    assert tops[-1] - tops[0] >= 50, f"{path.name}: fields too close {tops}"
    assert "This is typed" in html and "And this is typed again" in html, html


def check_ink_text_overlap(path: Path) -> None:
    xml, html = _export(path)
    ink = _ink_css_y_range(xml)
    assert ink is not None, f"{path.name}: no ink"
    tops = _abs_tops(html)
    assert len(tops) == 1, tops
    lo, hi = ink
    top = tops[0]
    assert lo - 80 <= top <= hi + 80, (
        f"{path.name}: text top={top:.1f} outside ink CSS y=[{lo:.1f},{hi:.1f}]"
    )


def main() -> None:
    ensure_fixture()
    check_text_ink_text_fields(FIXTURE)
    check_ink_text_overlap(RM / "text_and_strokes.rm")
    # blanks between runs → multiple fields (not one stacked blob)
    _, multi = _export(RM / "text_multiple_lines.rm")
    assert len(_abs_tops(multi)) >= 2, multi
    print("ok: text/ink/text fields + ink overlap")


if __name__ == "__main__":
    main()
