"""Fail if typed-text HTML line spacing gets crushed toward the top."""
from io import StringIO
from pathlib import Path
import re

from rmscene import read_tree
from rmscene import scene_items as si
from rmc.exporters.inmkl import tree_to_html
from rmc.exporters.svg import LINE_HEIGHTS

RM = Path(__file__).parent / "rm" / "text_multiple_lines.rm"


def main() -> None:
    with RM.open("rb") as f:
        tree = read_tree(f)
    out = StringIO()
    out.name = "check.html"
    tree_to_html(tree, out)
    tops = [float(t) for t in re.findall(r"top: ([0-9.]+)px", out.getvalue())]
    assert len(tops) >= 3, tops
    gaps = [b - a for a, b in zip(tops, tops[1:])]
    # PLAIN line height is 70 RM; CSS mapping must keep ~that, not ~26 from himetric/96dpi.
    plain = float(LINE_HEIGHTS[si.ParagraphStyle.PLAIN])
    assert min(gaps) >= plain - 1, (tops, gaps)
    assert tops[0] >= 500, tops  # Y_PAD title clearance still present
    print(f"ok tops={tops[:4]}… gaps={gaps[:3]}…")


if __name__ == "__main__":
    main()
