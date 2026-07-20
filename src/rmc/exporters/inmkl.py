__author__ = "Michael Kushnir"
__version__ = "1.1"

"""
Convert .rm SceneTree to InkML + OneNote HTML.

Coordinate system (one pipeline for ink and typed text)
-------------------------------------------------------
1. RM page units, origin at the frozen content bbox (min_x, min_y).
2. InkML:  rm_to_inkml() = (rm - origin) * RM_PER_INK + pad
   Channel units are labeled himetric (OneNote requirement). RM_PER_INK is the
   export scale (10), shared by every stroke and every text corner.
3. HTML CSS px: inkml_to_css() = inkml / RM_PER_INK
   so the same RM point yields matching ink and absolute HTML positions.
4. Text line Y uses the same values as build_anchor_pos() (ink group anchors),
   not SVG's draw_text slot bottom — otherwise type sits one LINE_HEIGHT below ink.

Pads (48, 120) CSS px match OneNote defaults below the title; stored in inkml units.
"""

from rmscene.scene_items import PenColor
import logging
from pathlib import Path
from rmscene import SceneTree
from .svg import build_anchor_pos, get_anchor, get_bounding_box, LINE_HEIGHTS, TEXT_TOP_Y
from rmscene import scene_items as si
from rmscene.text import TextDocument
from typing import List, Tuple
from .writing_tools import Pen, RM_PALETTE

# ----CONSTANTS----

A4_HEIGHT_MM = 297
A4_WIDTH_MM = 210
ASPECT_RATIO = A4_WIDTH_MM / A4_HEIGHT_MM

# RM → InkML scale (also brush size). CSS cancels this so RM deltas match.
RM_PER_INK = 10
WIDTH_CONV_CONSTANT = RM_PER_INK  # brush / legacy name
HEIGHT_CONV_CONSTANT = RM_PER_INK
PRESSURE_CONV_CONSTANT = 128

# OneNote HTML defaults below title (CSS px), expressed in InkML units.
CSS_X_PAD = 48
CSS_Y_PAD = 120
X_PAD = CSS_X_PAD * RM_PER_INK
Y_PAD = CSS_Y_PAD * RM_PER_INK

XML_HEADER = ("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
              "<inkml:ink xmlns:emma=\"http://www.w3.org/2003/04/emma\" "
                 "xmlns:msink=\"http://schemas.microsoft.com/ink/2010/main\""
                 " xmlns:inkml=\"http://www.w3.org/2003/InkML\">\n")

# ----GLOBAL VARIABLES----

min_x = min_y = max_x = max_y = 0
trace_id = 1
_logger = logging.getLogger(__name__)


# ----COORDINATE PIPELINE-----

def set_page_origin(bbox: Tuple[float, float, float, float]) -> None:
    """Freeze RM origin used by every later rm_to_inkml / rm_to_css call."""
    global min_x, max_x, min_y, max_y
    min_x, max_x, min_y, max_y = bbox


def rm_to_inkml(x: float, y: float) -> Tuple[int, int]:
    """RM page point → InkML channel integers (same transform for every stroke)."""
    return (
        int((x - min_x) * RM_PER_INK + X_PAD),
        int((y - min_y) * RM_PER_INK + Y_PAD),
    )


def inkml_to_css(value: float) -> float:
    """InkML channel value → CSS px (inverse of RM_PER_INK)."""
    return value / RM_PER_INK


def rm_to_css(x: float, y: float) -> Tuple[float, float]:
    """RM page point → HTML absolute CSS px. Same RM point as rm_to_inkml."""
    ix, iy = rm_to_inkml(x, y)
    return inkml_to_css(ix), inkml_to_css(iy)


# Legacy names used by brushes / older call sites
scale = rm_to_inkml
scale_to_css_px = inkml_to_css


def rm_line_height_css(style: si.ParagraphStyle) -> float:
    return float(LINE_HEIGHTS.get(style, 70))


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph_css(style: si.ParagraphStyle, props: dict) -> str:
    lh = rm_line_height_css(style)
    parts = [f"margin: 0", f"line-height: {lh:.2f}px"]
    if style == si.ParagraphStyle.HEADING:
        parts += ["font-size: 16pt", "font-weight: bold"]
    elif style == si.ParagraphStyle.BOLD:
        parts.append("font-weight: bold")
    elif style in (si.ParagraphStyle.BULLET, si.ParagraphStyle.BULLET2):
        parts.append("padding-left: 1.2em")
    for k, v in props.items():
        if k == "font-weight" and style in (si.ParagraphStyle.HEADING, si.ParagraphStyle.BOLD):
            continue
        parts.append(f"{k}: {v}")
    return "; ".join(parts)


def _format_line(p) -> str:
    raw = str(p).strip().replace("\u2028", "\n").replace("\u2029", "\n")
    if not raw:
        return ""
    if p.style.value in (si.ParagraphStyle.BULLET, si.ParagraphStyle.BULLET2):
        raw = "• " + raw
    return _html_escape(raw).replace("\n", "<br/>")


def _emit_run_inner(paragraphs) -> str:
    parts: List[str] = []
    plain_lines: List[str] = []
    plain_props: dict = {}

    def flush_plain():
        nonlocal plain_lines, plain_props
        if not plain_lines:
            return
        body = "<br/>".join(plain_lines)
        css = _paragraph_css(si.ParagraphStyle.PLAIN, plain_props)
        parts.append(f'<p style="{css}">{body}</p>')
        plain_lines = []
        plain_props = {}

    for p in paragraphs:
        style = p.style.value
        props = dict(p.contents[0].properties) if p.contents else {}
        line = _format_line(p)
        if style == si.ParagraphStyle.PLAIN:
            if not plain_lines:
                plain_props = props
            plain_lines.append(line)
            continue
        flush_plain()
        css = _paragraph_css(style, props)
        parts.append(f'<p style="{css}">{line}</p>')
    flush_plain()
    return "".join(parts)


def _text_runs(doc: TextDocument, text_pos_y: float):
    """Yield (paragraphs, absolute_rm_y) per non-blank run.

    absolute_rm_y matches build_anchor_pos (ink anchors), not svg.draw_text.
    """
    # Same walk as build_anchor_pos: record Y, then advance.
    ypos = text_pos_y + TEXT_TOP_Y
    run = []
    for p in doc.contents:
        if str(p).strip():
            run.append((p, ypos))
        elif run:
            yield run
            run = []
        ypos += LINE_HEIGHTS.get(p.style.value, 70)
    if run:
        yield run


def tree_to_xml(tree: SceneTree, output):
    """
    Traverses through a SceneTree and dumps all the data to the XML file, retaining accurate ink data.
    :param tree:  The SceneTree that is extracted from the .rm file.
    :param output: IO stream of the output XML file.
    """
    _logger.debug("Exporting %d items to InkML", len(list(tree.walk())))
    output.write(XML_HEADER)
    configure_ink(tree, output)
    global trace_id
    anchor_pos = build_anchor_pos(tree.root_text)
    set_page_origin(get_bounding_box(tree.root, anchor_pos))
    output.write("  <inkml:traceGroup>\n")
    draw_tree(tree.root, output, anchor_pos)
    output.write("  </inkml:traceGroup>\n")
    _logger.debug("Finished InkML export: %d traces", trace_id - 1)
    output.write("</inkml:ink>\n")


def draw_tree(item: si.Group, output, anchor_pos, move_pos=(0, 0)):
    for child_id in item.children:
        child = item.children[child_id]
        _logger.debug("Group child: %s %s", child_id, type(child))
        if isinstance(child, si.Group):
            move_x, move_y = move_pos
            x, y = get_anchor(child, anchor_pos)
            draw_tree(child, output, anchor_pos, (x + move_x, y + move_y))
        if isinstance(child, si.Line):
            global trace_id
            draw_stroke(child, output, trace_id, move_pos)
            trace_id += 1


def configure_ink(tree: SceneTree, output):
    output.write("  <inkml:definitions>")
    output.write("""
    <inkml:context xml:id="ctxCoordinatesWithPressure">
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
    </inkml:context>
    """)
    pens_set = fetch_used_inks(tree)
    for pen in pens_set:
        output.write(f"""
    <inkml:brush xml:id="{generate_id_from_pen(pen)}">
        <inkml:brushProperty name="width" value="{int(pen.stroke_width * WIDTH_CONV_CONSTANT)}" units="himetric" />
        <inkml:brushProperty name="height" value="{int(pen.stroke_width * HEIGHT_CONV_CONSTANT)}" units="himetric" />
        <inkml:brushProperty name="color" value="{'#%02x%02x%02x' % RM_PALETTE[pen.stroke_color]}" />
        <inkml:brushProperty name="transparency" value="{1 - pen.stroke_opacity}" />
        <inkml:brushProperty name="tip" value="ellipse" />
        <inkml:brushProperty name="rasterOp" value="{'maskPen' if pen.name == 'Highlighter' else 'copyPen'}" />
        <inkml:brushProperty name="ignorePressure" value="false" />
        <inkml:brushProperty name="antiAliased" value="true" />
        <inkml:brushProperty name="fitToCurve" value="false" />
    </inkml:brush>""")
    output.write("\n  </inkml:definitions>\n")


def generate_id_from_pen(pen: Pen):
    return (f"name_{pen.name}_cap_{pen.stroke_linecap}_op_{pen.stroke_opacity}_w_"
            f"{pen.stroke_width}_clr_{pen.stroke_color}")


def fetch_used_inks(tree: SceneTree) -> List[Pen]:
    pens = []
    ink_ids = []
    for item in tree.walk():
        if isinstance(item, si.Line):
            color = item.color.value if item.color.value != 9 else PenColor.YELLOW.value
            pen = Pen.create(item.tool.value, color, item.thickness_scale)
            gen_id = generate_id_from_pen(pen)
            if gen_id not in ink_ids:
                ink_ids.append(gen_id)
                pens.append(pen)
    return pens


def draw_stroke(item: si.Line, output, trace_id: int, move_pos: Tuple[int, int] = (0, 0)) -> None:
    if _logger.root.level == logging.DEBUG:
        _logger.debug("Drawing stroke %d from node %s with %d points", trace_id, item.node_id, len(item.points))
    tid = str(trace_id)
    coord = []
    move_x, move_y = move_pos
    for pt in item.points:
        scaled_x, scaled_y = rm_to_inkml(pt.x + move_x, pt.y + move_y)
        scaled_pressure = int(pt.pressure * PRESSURE_CONV_CONSTANT)
        coord.append(f"{scaled_x} {scaled_y} {scaled_pressure}")
    coord_str = ",".join(coord)
    color = item.color.value if item.color.value != 9 else PenColor.YELLOW.value
    pen = Pen.create(item.tool.value, color, item.thickness_scale)
    brush_id = generate_id_from_pen(pen)
    output.write(
        f"    <inkml:trace xml:id=\"{tid}\" contextRef=\"#ctxCoordinatesWithPressure\" "
        f"brushRef=\"#{brush_id}\">{coord_str}</inkml:trace>\n"
    )


def tree_to_html(tree: SceneTree, output):
    """Emit OneNote HTML using the same RM→inkml→CSS map as tree_to_xml."""
    text = tree.root_text
    anchor_pos = build_anchor_pos(tree.root_text)
    set_page_origin(get_bounding_box(tree.root, anchor_pos))

    page_title = Path(output.name).stem
    output.write(f"""<html>
    <head>
        <title>{page_title}</title>
    </head>
    <body data-absolute-enabled="true" style="font-family:Calibri;font-size:11pt">""")
    if text is not None:
        doc = TextDocument.from_scene_item(text)
        width_px = float(text.width)
        for run in _text_runs(doc, text.pos_y):
            _p0, abs_y = run[0]
            left, top = rm_to_css(text.pos_x, abs_y)
            inner = _emit_run_inner([p for p, _y in run])
            output.write(
                f"""
                <div style="position: absolute; left: {left:.2f}px; top: {top:.2f}px; width: {width_px:.2f}px">
                    {inner}
                </div>"""
            )
    output.write("""
    </body>
</html>""")
