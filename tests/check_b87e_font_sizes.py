"""Ground-truth: tests/rm/b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm

Four typed lines with ink boxes (title → … → body). Format styles are
HEADING, BOLD, BOLD, PLAIN — two middle lines share BOLD in the .rm; ink
boxes still give four Y bands for alignment checks.

Run: poetry run python tests/check_b87e_font_sizes.py
"""
from __future__ import annotations

from pathlib import Path

from rmscene import read_tree
from rmscene import scene_items as si
from rmscene.text import TextDocument
from rmc.exporters.inmkl import html_text_origin_css, rm_to_css, set_page_origin, tree_to_html
from rmc.exporters.svg import LINE_HEIGHTS, TEXT_TOP_Y, build_anchor_pos, get_anchor, get_bounding_box
from io import StringIO

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"

# Expected text + ParagraphStyle (device UI sizes; .rm encodes only these).
EXPECTED = [
    ("This is the largest", si.ParagraphStyle.HEADING),
    ("Then this is the second", si.ParagraphStyle.BOLD),
    ("This would be the third", si.ParagraphStyle.BOLD),
    ("This is normal text", si.ParagraphStyle.PLAIN),
]


def _strokes(tree, anchors):
    out = []

    def walk(item, move=(0.0, 0.0)):
        for child in item.children.values():
            if isinstance(child, si.Group):
                ax, ay = get_anchor(child, anchors)
                walk(child, (move[0] + ax, move[1] + ay))
            elif isinstance(child, si.Line) and len(child.points) >= 2:
                xs = [pt.x + move[0] for pt in child.points]
                ys = [pt.y + move[1] for pt in child.points]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if w >= 40 and h >= 20:  # skip dots / scrap
                    out.append((min(xs), max(xs), min(ys), max(ys), h))

    walk(tree.root)
    out.sort(key=lambda r: r[2])  # top → bottom
    return out


def _typed_lines(text):
    doc = TextDocument.from_scene_item(text)
    lines = []
    ypos = text.pos_y + TEXT_TOP_Y
    for p in doc.contents:
        s = str(p).strip()
        if s:
            lines.append((s, p.style.value, ypos))
        ypos += LINE_HEIGHTS.get(p.style.value, 70)
    return lines


def main() -> None:
    assert RM.is_file(), RM
    with RM.open("rb") as f:
        tree = read_tree(f)
    text = tree.root_text
    assert text is not None

    lines = _typed_lines(text)
    assert len(lines) == 4, lines
    for (got_s, got_st, _y), (exp_s, exp_st) in zip(lines, EXPECTED):
        assert got_s == exp_s, (got_s, exp_s)
        assert got_st == exp_st, (got_s, got_st, exp_st)

    anchors = build_anchor_pos(text)
    set_page_origin(get_bounding_box(tree.root, anchors))
    boxes = _strokes(tree, anchors)
    assert len(boxes) >= 4, f"want ≥4 ink boxes, got {boxes}"

    # Each typed Y sits inside the nearest box by Y; boxes shrink down the page.
    heights = [b[4] for b in boxes[:4]]
    assert heights == sorted(heights, reverse=True), f"box heights not descending: {heights}"

    for s, st, y in lines:
        near = min(boxes, key=lambda b: abs((b[2] + b[3]) / 2 - y))
        x0, x1, y0, y1, _h = near
        assert y0 <= y <= y1, f"{s!r} y={y} outside box y=[{y0},{y1}]"
        # Boxes hug glyphs, not full text column — require X overlap with column.
        col0, col1 = text.pos_x, text.pos_x + float(text.width)
        assert x1 >= col0 and x0 <= col1, f"{s!r} box x=[{x0},{x1}] misses column [{col0},{col1}]"
        left, top = html_text_origin_css(text.pos_x, y, st)
        assert left > 0 and top > 0, (s, left, top)

    # Export keeps all four strings (may share one absolute run if no blank lines).
    buf = StringIO()
    buf.name = RM.stem + ".html"
    with RM.open("rb") as f:
        tree_to_html(read_tree(f), buf)
    html = buf.getvalue()
    for s, _st in EXPECTED:
        assert s in html, s
    assert "33.3pt" in html and "23.51pt" in html and "15.42pt" in html and "13.71pt" in html, html
    assert "position:absolute" in html
    # Installed Windows names (webui VF); Style.qml uses Serif Small / Sans.
    assert html.count("reMarkable Serif VF") >= 2
    assert html.count("reMarkable Sans VF") >= 2
    assert "This would be the third" in html
    third = html.split("This would be the third")[0].rsplit("font-family:", 1)[-1]
    assert third.startswith("reMarkable Sans VF"), third[:60]
    second = html.split("Then this is the second")[0].rsplit("font-family:", 1)[-1]
    assert second.startswith("reMarkable Serif VF"), second[:60]

    print(
        f"ok b87e: 4 lines + {len(boxes)} boxes; "
        f"heights={heights}; styles={[st.name for _s, st, _y in lines]}"
    )


if __name__ == "__main__":
    main()
