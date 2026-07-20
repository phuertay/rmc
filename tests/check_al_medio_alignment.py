"""Ground-truth alignment: tests/rm/al_medio.rm (+ tests/expected/al_medio.pdf).

Page: handwriting above, typed \"Al medio\" inside a hand-drawn rectangle,
handwriting below. Typed center must sit inside the rectangle's RM bounds;
above/below ink must not swallow the box.
"""
from __future__ import annotations

from pathlib import Path

from rmscene import CrdtId, read_tree
from rmscene import scene_items as si
from rmscene.text import TextDocument
from rmc.exporters.inmkl import rm_to_css, set_page_origin
from rmc.exporters.svg import (
    ANCHOR_AFTER_TEXT,
    ANCHOR_BEFORE_TEXT,
    TEXT_TOP_Y,
    build_anchor_pos,
    get_anchor,
    get_bounding_box,
)

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "al_medio.rm"
EXPECTED_PDF = ROOT / "expected" / "al_medio.pdf"


def _regions(tree, anchors):
    top, box, bot = [], [], []

    def walk(item, move=(0.0, 0.0), tag="?"):
        for child in item.children.values():
            if isinstance(child, si.Group):
                ax, ay = get_anchor(child, anchors)
                ntag = tag
                if child.anchor_id is not None:
                    aid = child.anchor_id.value
                    if aid == ANCHOR_BEFORE_TEXT:
                        ntag = "top"
                    elif aid == ANCHOR_AFTER_TEXT:
                        ntag = "bot"
                    else:
                        ntag = "box"
                walk(child, (move[0] + ax, move[1] + ay), ntag)
            elif isinstance(child, si.Line) and child.points:
                xs = [pt.x + move[0] for pt in child.points]
                ys = [pt.y + move[1] for pt in child.points]
                bucket = {"top": top, "bot": bot, "box": box}.get(tag)
                if bucket is not None:
                    bucket.append((min(xs), max(xs), min(ys), max(ys)))

    walk(tree.root)
    return top, box, bot


def _span(rects):
    return (
        min(r[0] for r in rects),
        max(r[1] for r in rects),
        min(r[2] for r in rects),
        max(r[3] for r in rects),
    )


def main() -> None:
    assert RM.is_file(), RM
    assert EXPECTED_PDF.is_file(), EXPECTED_PDF

    with RM.open("rb") as f:
        tree = read_tree(f)
    text = tree.root_text
    assert text is not None
    doc = TextDocument.from_scene_item(text)
    assert any("Al medio" in str(p) for p in doc.contents), doc.contents

    anchors = build_anchor_pos(text)
    set_page_origin(get_bounding_box(tree.root, anchors))
    top, box, bot = _regions(tree, anchors)
    assert box, "missing hand-drawn rectangle around typed text"
    assert top and bot, "missing handwriting above/below"

    bx0, bx1, by0, by1 = _span(box)
    _tx0, _tx1, ty0, ty1 = _span(top)
    _ox0, _ox1, oy0, oy1 = _span(bot)

    # Typed line uses the same Y as ink character anchors / build_anchor_pos.
    typed_y = None
    ypos = text.pos_y + TEXT_TOP_Y
    from rmc.exporters.svg import LINE_HEIGHTS

    for p in doc.contents:
        if "Al medio" in str(p):
            typed_y = ypos
            break
        ypos += LINE_HEIGHTS.get(p.style.value, 70)
    assert typed_y is not None, "Al medio paragraph not found"

    assert by0 <= typed_y <= by1, f"typed y={typed_y} outside box y=[{by0},{by1}]"
    assert bx0 <= text.pos_x <= bx1, f"typed x={text.pos_x} outside box x=[{bx0},{bx1}]"

    # Vertical order: above handwriting ends near/above box; below starts under typed line.
    assert ty1 < by1, f"top ink extends past box bottom: top_y1={ty1} box_y1={by1}"
    assert oy0 > typed_y, f"bottom ink overlaps typed line: bot_y0={oy0} typed={typed_y}"
    assert anchors[ANCHOR_AFTER_TEXT] > anchors[ANCHOR_BEFORE_TEXT]

    # HTML CSS path must land on the same RM point.
    left, top_css = rm_to_css(text.pos_x, typed_y)
    assert left > 0 and top_css > 0, (left, top_css)

    print(
        f"ok al_medio: typed=({text.pos_x:.0f},{typed_y:.0f}) "
        f"inside box x=[{bx0:.0f},{bx1:.0f}] y=[{by0:.0f},{by1:.0f}]; "
        f"css=({left:.0f},{top_css:.0f})"
    )


if __name__ == "__main__":
    main()
