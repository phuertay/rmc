"""OneNote InkML/HTML layout checks + fixture builder.

Fixtures:
  tests/rm/text_and_strokes.rm  — ink + typed word (alignment)
  tests/rm/text_multiple_lines.rm — many typed lines (one field)
  tests/rm/onenote_text_block.rm — generated multi-line plain text

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
FIXTURE = RM / "onenote_text_block.rm"


def _export(path: Path) -> tuple[str, str]:
    with path.open("rb") as f:
        tree = read_tree(f)
    xml_buf, html_buf = StringIO(), StringIO()
    xml_buf.name = path.stem + ".xml"
    html_buf.name = path.stem + ".html"
    tree_to_xml(tree, xml_buf)
    # tree_to_xml mutates globals; re-read for a clean html pass
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


def _abs_divs(html: str) -> list[str]:
    return re.findall(r'<div style="position: absolute;[^"]*"[^>]*>', html)


def ensure_fixture() -> Path:
    """Write a checked-in multi-line typed-text .rm if missing/outdated."""
    text = "Line one\nLine two\nLine three\n\nAfter a blank line"
    buf = BytesIO()
    write_blocks(buf, simple_text_document(text))
    FIXTURE.write_bytes(buf.getvalue())
    return FIXTURE


def check_one_text_field(path: Path) -> None:
    _, html = _export(path)
    divs = _abs_divs(html)
    assert len(divs) == 1, f"{path.name}: want 1 absolute text field, got {len(divs)}\n{html}"
    # Multi-line notebook text → one field: either several <p> or one <p> with <br/>.
    assert html.count("<p ") >= 1 and (
        html.count("<p ") >= 2 or "<br/>" in html
    ), f"{path.name}: expected multi-line content in one div\n{html}"


def check_ink_text_overlap(path: Path) -> None:
    xml, html = _export(path)
    ink = _ink_css_y_range(xml)
    assert ink is not None, f"{path.name}: no ink"
    m = re.search(r"top: ([0-9.]+)px", html)
    assert m, html
    top = float(m.group(1))
    lo, hi = ink
    # Typed block must sit in the same vertical band as ink (not a page below).
    assert lo - 80 <= top <= hi + 80, (
        f"{path.name}: text top={top:.1f} outside ink CSS y=[{lo:.1f},{hi:.1f}]"
    )


def main() -> None:
    ensure_fixture()
    check_one_text_field(FIXTURE)
    check_one_text_field(RM / "text_multiple_lines.rm")
    check_ink_text_overlap(RM / "text_and_strokes.rm")
    print("ok: one text field + ink/text overlap")


if __name__ == "__main__":
    main()
