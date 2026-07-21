__author__ = "Michael Kushnir"
__version__ = "1.1"

"""
Convert .rm SceneTree to InkML + OneNote HTML.

Coordinate system (one pipeline for ink and typed text)
-------------------------------------------------------
1. RM page units, origin at the frozen content bbox (min_x, min_y).
2. InkML:  rm_to_inkml() = (rm - origin) * RM_PER_INK + pad
   Channel units are real himetric (1 inch = 2540). RM_PER_INK = 2540/SCREEN_DPI
   so 1 RM screen-pixel = 1/SCREEN_DPI inch.
3. HTML CSS px: inkml_to_css() = round(inkml * 96/2540) + CSS_ALIGN_*
   Same RM point → matching absolute HTML (OneNote calib 2026-07-20).
   OneNote zeros fractional left/top to 0,0 — CSS positions must be integers.
   CSS_ALIGN_* on HTML; strokes add CSS_ALIGN_DX + INK_EXTRA_* so the box
   clears typed text (live-tuned on al_medio).
4. Text line Y uses the same values as build_anchor_pos() (ink group anchors),
   not SVG's draw_text slot bottom — otherwise type sits one LINE_HEIGHT below ink.
5. HEADING HTML top is shifted up by OneNote's <p> 5.5pt margin plus ~font ascent
   so the glyph baseline lands on the RM anchor (large titles otherwise sit on ink).
6. Ink uses one page-wide INK_SCALE about each group's left edge + mid-Y
   (handwriting size must stay consistent). HTML font sizes absorb the
   remaining box/glyph mismatch. Per-style DX/DY nudges only.

Pads (48, 120) CSS px match OneNote defaults below the title; stored in himetric.
"""

from rmscene.scene_items import PenColor
import logging
from pathlib import Path
from rmscene import SceneTree
from .svg import (
    SCREEN_DPI,
    build_anchor_pos,
    get_anchor,
    get_bounding_box,
    LINE_HEIGHTS,
    TEXT_TOP_Y,
)
from rmscene import scene_items as si
from rmscene.text import TextDocument
from typing import List, Tuple
from .writing_tools import Pen, RM_PALETTE

# ----CONSTANTS----

A4_HEIGHT_MM = 297
A4_WIDTH_MM = 210
ASPECT_RATIO = A4_WIDTH_MM / A4_HEIGHT_MM

HIMETRIC_PER_INCH = 2540
CSS_DPI = 96
# Physical himetric per RM unit (RM coords are screen pixels at SCREEN_DPI).
RM_PER_INK = HIMETRIC_PER_INCH / SCREEN_DPI
CSS_PER_HIMETRIC = CSS_DPI / HIMETRIC_PER_INCH  # 96/2540
# Ink-only size vs HTML type. One page-wide scale (handwriting must match).
# step1-calibS 20260721-230817: L1 mid 3↔4, L2 mid 2↔3 → page S = avg.
INK_SCALE = 1.5875
WIDTH_CONV_CONSTANT = RM_PER_INK * INK_SCALE
HEIGHT_CONV_CONSTANT = RM_PER_INK * INK_SCALE
PRESSURE_CONV_CONSTANT = 128

# OneNote HTML defaults below title (CSS px), expressed in himetric.
CSS_X_PAD = 48
CSS_Y_PAD = 120
X_PAD = CSS_X_PAD / CSS_PER_HIMETRIC
Y_PAD = CSS_Y_PAD / CSS_PER_HIMETRIC

# Residual OneNote origin (rmc-calib-20260720-203433): green + was ~3/4
# quarter-tick right and 2 quarter-ticks down from ink center. Nudge opposite.
# Chosen vs 204924 (−7,−19) over 205232 (−7,−20).
# Y: HTML-only CSS_ALIGN_DY; tiny ink-only DY from live al_medio tweak.
# X: strokes get CSS_ALIGN_DX + small extra so box clears "A".
# ponytail: empirical; last nudge after real EB Garamond/Noto Sans install
# (fallback metrics left boxes low — upper stroke through glyphs).
_CSS_TICK = 250 * CSS_PER_HIMETRIC
CSS_ALIGN_DX = -round(0.75 * _CSS_TICK)  # -7
CSS_ALIGN_DY = -round(2.0 * _CSS_TICK)  # -19
INK_ALIGN_DX = round(CSS_ALIGN_DX / CSS_PER_HIMETRIC)  # himetric, strokes only
INK_EXTRA_DX_CSS = 0  # default / HEADING (b87e-DX-6of7)
# Per-style ink DX (CSS px). L2 slightly off with shared DX — ladder next.
INK_EXTRA_DX_HEADING_CSS = 0
INK_EXTRA_DX_BOLD_CSS = 0  # first BOLD (L2); b87e-L2DX-4of7
INK_EXTRA_DX_SECOND_BOLD_CSS = 0
INK_EXTRA_DX_PLAIN_CSS = 0
# No vertical ink nudge (desktop DY ladders reverted).
PAGE_NUDGE_DY_CSS = 0
INK_EXTRA_DY_CSS = 0
INK_EXTRA_DY_HEADING_CSS = 0
INK_EXTRA_DY_BOLD_CSS = 0
INK_EXTRA_DY_SECOND_BOLD_CSS = 0
INK_EXTRA_DY_PLAIN_CSS = 0
INK_EXTRA_DX = round(INK_EXTRA_DX_CSS / CSS_PER_HIMETRIC)
INK_EXTRA_DY = round(INK_EXTRA_DY_CSS / CSS_PER_HIMETRIC)

XML_HEADER = ("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
              "<inkml:ink xmlns:emma=\"http://www.w3.org/2003/04/emma\" "
                 "xmlns:msink=\"http://schemas.microsoft.com/ink/2010/main\""
                 " xmlns:inkml=\"http://www.w3.org/2003/InkML\">\n")

# ----GLOBAL VARIABLES----

min_x = min_y = max_x = max_y = 0
# Fallback center when no per-group scale (page content mid).
_ink_cx = _ink_cy = 0.0
# (y_rm, sx, sy, dx_css, dy_css) for nearest-text lookup; set in prepare_ink_scales.
_ink_scale_ys: List[Tuple[float, float, float, float, float]] = []
trace_id = 1
_logger = logging.getLogger(__name__)


# ----COORDINATE PIPELINE-----

def set_page_origin(bbox: Tuple[float, float, float, float]) -> None:
    """Freeze RM origin used by every later rm_to_inkml / rm_to_css call."""
    global min_x, max_x, min_y, max_y, _ink_cx, _ink_cy
    min_x, max_x, min_y, max_y = bbox
    _ink_cx = 0.5 * (min_x + max_x)
    _ink_cy = 0.5 * (min_y + max_y)


def rm_ink_scale_for_style(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    """Page-wide ink scale (style ignored — handwriting stays consistent)."""
    return INK_SCALE


def rm_ink_scale_x_for_style(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    return INK_SCALE


def rm_ink_extra_dx_css_for_style(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    """Per-line ink X nudge (CSS px)."""
    if style == si.ParagraphStyle.HEADING:
        return INK_EXTRA_DX_HEADING_CSS
    if style == si.ParagraphStyle.BOLD:
        return INK_EXTRA_DX_SECOND_BOLD_CSS if bold_ordinal > 1 else INK_EXTRA_DX_BOLD_CSS
    return INK_EXTRA_DX_PLAIN_CSS


def rm_ink_extra_dy_css_for_style(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    """Per-line ink Y nudge (CSS px). Smaller type needs more lift on b87e."""
    if style == si.ParagraphStyle.HEADING:
        return INK_EXTRA_DY_HEADING_CSS
    if style == si.ParagraphStyle.BOLD:
        return INK_EXTRA_DY_SECOND_BOLD_CSS if bold_ordinal > 1 else INK_EXTRA_DY_BOLD_CSS
    return INK_EXTRA_DY_PLAIN_CSS


def prepare_ink_scales(tree: SceneTree) -> None:
    """Map each typed paragraph Y → (sx, sy, dx_css, dy_css)."""
    global _ink_scale_ys
    _ink_scale_ys = []
    text = tree.root_text
    if text is None:
        return
    doc = TextDocument.from_scene_item(text)
    ypos = text.pos_y + TEXT_TOP_Y
    bold_n = 0
    for p in doc.contents:
        if str(p).strip():
            st = p.style.value
            bold_ord = 1
            if st == si.ParagraphStyle.BOLD:
                bold_n += 1
                bold_ord = bold_n
            _ink_scale_ys.append(
                (
                    ypos,
                    rm_ink_scale_x_for_style(st, bold_ordinal=bold_ord),
                    rm_ink_scale_for_style(st, bold_ordinal=bold_ord),
                    rm_ink_extra_dx_css_for_style(st, bold_ordinal=bold_ord),
                    rm_ink_extra_dy_css_for_style(st, bold_ordinal=bold_ord),
                )
            )
        ypos += LINE_HEIGHTS.get(p.style.value, 70)


def nearest_ink_params(y_rm: float) -> Tuple[float, float, float, float]:
    """Return (sx, sy, dx_css, dy_css) for the typed line nearest to y_rm."""
    if not _ink_scale_ys:
        return INK_SCALE, INK_SCALE, INK_EXTRA_DX_CSS, INK_EXTRA_DY_CSS
    _y, sx, sy, dx, dy = min(_ink_scale_ys, key=lambda t: abs(t[0] - y_rm))
    return sx, sy, dx, dy


def nearest_ink_scale(y_rm: float) -> float:
    """Height scale (sy) — used by size checks."""
    return nearest_ink_params(y_rm)[1]


def rm_to_inkml(x: float, y: float) -> Tuple[int, int]:
    """RM page point → InkML channel integers (pad only; stroke X nudge in draw_stroke)."""
    return (
        int((x - min_x) * RM_PER_INK + X_PAD),
        int((y - min_y) * RM_PER_INK + Y_PAD),
    )


def rm_to_inkml_stroke(
    x: float,
    y: float,
    *,
    cx: float | None = None,
    cy: float | None = None,
    scale_x: float | None = None,
    scale_y: float | None = None,
    scale: float | None = None,
) -> Tuple[int, int]:
    """RM point → InkML; anisotropic scale about left edge + mid-Y."""
    sx = INK_SCALE if scale_x is None else scale_x
    sy = INK_SCALE if scale_y is None else scale_y
    if scale is not None and scale_x is None and scale_y is None:
        sx = sy = scale
    ox = _ink_cx if cx is None else cx
    oy = _ink_cy if cy is None else cy
    if sx != 1.0:
        x = (x - ox) * sx + ox
    if sy != 1.0:
        y = (y - oy) * sy + oy
    return rm_to_inkml(x, y)


def inkml_to_css(value: float) -> float:
    """InkML himetric → CSS px at 96 DPI.

    Rounded to int: OneNote Graph drops fractional left/top to 0,0.
    """
    return float(round(value * CSS_PER_HIMETRIC))


def rm_delta_to_css(delta_rm: float) -> float:
    """RM length (no pad) → CSS px (integer)."""
    return float(round(delta_rm * RM_PER_INK * CSS_PER_HIMETRIC))


def rm_to_css(x: float, y: float) -> Tuple[float, float]:
    """RM page point → HTML absolute CSS px (InkML path + HTML-only CSS_ALIGN)."""
    ix, iy = rm_to_inkml(x, y)
    return (
        inkml_to_css(ix) + CSS_ALIGN_DX,
        inkml_to_css(iy) + CSS_ALIGN_DY + PAGE_NUDGE_DY_CSS,
    )


def html_text_origin_css(
    rm_x: float, rm_y: float, style: si.ParagraphStyle
) -> Tuple[float, float]:
    """CSS left/top for a text run.

    RM/SVG Y is a baseline; HTML top is the line-box top. HEADING needs a
    partial raise so ink neither sits on the glyph bottoms nor clips the tops
    (bd4c554f). Plain @11pt already matches al_medio — leave it.
    """
    left, top = rm_to_css(rm_x, rm_y)
    if style == si.ParagraphStyle.HEADING:
        top -= ONENOTE_P_MARGIN_PX
        # Real EB Garamond: box still low vs title — lower text (+8 vs prior +2).
        # ponytail: leave global ink (al_medio OK on desktop).
        top -= round(rm_font_size_css(style) * TEXT_ASCENT_RATIO) - 8
    return left, float(round(top))


# Legacy names used by brushes / older call sites
scale = rm_to_inkml
scale_to_css_px = inkml_to_css


def rm_line_height_css(style: si.ParagraphStyle) -> float:
    return rm_delta_to_css(float(LINE_HEIGHTS.get(style, 70)))


# Device faces (b87e PDF glyph outlines + remarkable fontconfig):
#   title + first mid (BOLD#1) → EB Garamond; second mid (BOLD#2) + body → Noto Sans.
# OneNote cannot embed fonts; stack closest Windows/Office stand-ins after.
# ponytail: install EB Garamond + Noto Sans for a true match.
FONT_FAMILY_SANS = "'Noto Sans','Segoe UI',Arial,sans-serif"
FONT_FAMILY_SERIF = "'EB Garamond',Garamond,'Palatino Linotype',Palatino,Georgia,serif"
FONT_SIZE_PT = {
    # L1 ≈ box*S; L2–L4 follow device PDF glyph-height ratios (not ink-box
    # heights — boxes are padded, which made L3/L4 huge vs real type).
    si.ParagraphStyle.HEADING: 40.0,
    si.ParagraphStyle.BOLD: 23.0,
    si.ParagraphStyle.PLAIN: 15.5,
    si.ParagraphStyle.BULLET: 15.5,
    si.ParagraphStyle.BULLET2: 15.5,
    si.ParagraphStyle.CHECKBOX: 15.5,
    si.ParagraphStyle.CHECKBOX_CHECKED: 15.5,
}
# Second+ ParagraphStyle.BOLD on a page (b87e “third” line) — format has no 4th style.
FONT_SIZE_SECOND_BOLD = 17.5
# Graph always wraps absolute-div text in <p style="margin-top:5.5pt">.
ONENOTE_P_MARGIN_PX = round(5.5 * CSS_DPI / 72)  # 7
# Partial ascent for HEADING only (0.8 overshot above the ink box).
TEXT_ASCENT_RATIO = 0.35
# CSS line-height as em of font — RM LINE_HEIGHTS is inter-paragraph gap, not
# the glyph box (64px on a 20pt title left a huge empty line box).
TEXT_LINE_HEIGHT_EM = 1.2


def rm_font_size_pt(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    if style == si.ParagraphStyle.BOLD and bold_ordinal > 1:
        return FONT_SIZE_SECOND_BOLD
    return FONT_SIZE_PT.get(style, 8.0)


def _fmt_pt(pt: float) -> str:
    """CSS font-size with optional half-point (OneNote accepts 10.5pt)."""
    return f"{pt:g}pt"


def rm_font_size_css(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> float:
    """CSS font-size (px) from style pt table."""
    return float(round(rm_font_size_pt(style, bold_ordinal=bold_ordinal) * CSS_DPI / 72))


def _font_family(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> str:
    # Device PDF outlines (b87e): L1 HEADING + L2 first BOLD → EB Garamond;
    # L3 second BOLD + L4 PLAIN → Noto Sans. (.rm stores L2/L3 both as BOLD.)
    if style == si.ParagraphStyle.HEADING:
        return FONT_FAMILY_SERIF
    if style == si.ParagraphStyle.BOLD and bold_ordinal == 1:
        return FONT_FAMILY_SERIF
    return FONT_FAMILY_SANS


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _format_line(p) -> str:
    raw = str(p).strip().replace("\u2028", "\n").replace("\u2029", "\n")
    if not raw:
        return ""
    if p.style.value in (si.ParagraphStyle.BULLET, si.ParagraphStyle.BULLET2):
        raw = "• " + raw
    return _html_escape(raw).replace("\n", "<br/>")


def _run_span_style(style: si.ParagraphStyle, *, bold_ordinal: int = 1) -> str:
    """Typography OneNote keeps on <span> (div styles get stripped; <p> gets 5.5pt margins)."""
    parts = [
        f"font-family:{_font_family(style, bold_ordinal=bold_ordinal)}",
        f"font-size:{_fmt_pt(rm_font_size_pt(style, bold_ordinal=bold_ordinal))}",
        f"line-height:{TEXT_LINE_HEIGHT_EM}",
    ]
    if style in (si.ParagraphStyle.BULLET, si.ParagraphStyle.BULLET2):
        parts.append("padding-left:1.2em")
    return ";".join(parts)


def _emit_run_inner(paragraphs, *, bold_ordinal: int = 1) -> str:
    """Join run lines with <br/> inside one styled span (no <p>)."""
    if not paragraphs:
        return ""
    style0 = paragraphs[0].style.value
    bits = []
    for p in paragraphs:
        line = _format_line(p)
        if not line:
            continue
        if p.style.value == style0:
            bits.append(line)
        else:
            bits.append(
                f'<span style="{_run_span_style(p.style.value, bold_ordinal=bold_ordinal)}">{line}</span>'
            )
    body = "<br/>".join(bits)
    return f'<span style="{_run_span_style(style0, bold_ordinal=bold_ordinal)}">{body}</span>'


def _text_runs(doc: TextDocument, text_pos_y: float):
    """Yield one (paragraphs, absolute_rm_y) per non-blank paragraph.

    absolute_rm_y matches build_anchor_pos (ink anchors), not svg.draw_text.
    One div per paragraph so mixed styles (b87e title/heading/body) keep RM Y.
    """
    ypos = text_pos_y + TEXT_TOP_Y
    for p in doc.contents:
        if str(p).strip():
            yield [(p, ypos)]
        ypos += LINE_HEIGHTS.get(p.style.value, 70)

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
    prepare_ink_scales(tree)
    output.write("  <inkml:traceGroup>\n")
    draw_tree(tree.root, output, anchor_pos)
    output.write("  </inkml:traceGroup>\n")
    _logger.debug("Finished InkML export: %d traces", trace_id - 1)
    output.write("</inkml:ink>\n")


def _group_scale_pivot(lines: list, move_pos: Tuple[float, float]) -> Tuple[float, float]:
    """Scale pivot: left edge (SX) + vertical mid (SY)."""
    mx, my = move_pos
    xs, ys = [], []
    for line in lines:
        for pt in line.points:
            xs.append(pt.x + mx)
            ys.append(pt.y + my)
    return min(xs), 0.5 * (min(ys) + max(ys))


def draw_tree(item: si.Group, output, anchor_pos, move_pos=(0, 0)):
    lines = [c for c in item.children.values() if isinstance(c, si.Line)]
    scale_ctx = None
    if lines:
        # Group move_pos Y matches typed-line anchor on b87e → pick sx/sy/DX/DY.
        sx, sy, dx_css, dy_css = nearest_ink_params(move_pos[1])
        cx, cy = _group_scale_pivot(lines, move_pos)
        dx_hm = round(dx_css / CSS_PER_HIMETRIC)
        dy_hm = round(dy_css / CSS_PER_HIMETRIC)
        scale_ctx = (cx, cy, sx, sy, dx_hm, dy_hm)
    for child_id in item.children:
        child = item.children[child_id]
        _logger.debug("Group child: %s %s", child_id, type(child))
        if isinstance(child, si.Group):
            move_x, move_y = move_pos
            x, y = get_anchor(child, anchor_pos)
            draw_tree(child, output, anchor_pos, (x + move_x, y + move_y))
        if isinstance(child, si.Line):
            global trace_id
            draw_stroke(child, output, trace_id, move_pos, scale_ctx=scale_ctx)
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


def draw_stroke(
    item: si.Line,
    output,
    trace_id: int,
    move_pos: Tuple[int, int] = (0, 0),
    scale_ctx: Tuple[float, float, float, float, int, int] | None = None,
) -> None:
    if _logger.root.level == logging.DEBUG:
        _logger.debug("Drawing stroke %d from node %s with %d points", trace_id, item.node_id, len(item.points))
    tid = str(trace_id)
    coord = []
    move_x, move_y = move_pos
    cx = cy = sx = sy = None
    dx, dy = INK_EXTRA_DX, INK_EXTRA_DY
    if scale_ctx is not None:
        cx, cy, sx, sy, dx, dy = scale_ctx
    for pt in item.points:
        scaled_x, scaled_y = rm_to_inkml_stroke(
            pt.x + move_x, pt.y + move_y, cx=cx, cy=cy, scale_x=sx, scale_y=sy
        )
        scaled_x += INK_ALIGN_DX + dx
        scaled_y += dy
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
    # Typography on absolute divs (not <p>) — Graph rewrites p margins to 5.5pt.
    output.write(f"""<html>
    <head>
        <title>{page_title}</title>
    </head>
    <body data-absolute-enabled="true" style="font-family:{FONT_FAMILY_SANS};font-size:{_fmt_pt(rm_font_size_pt(si.ParagraphStyle.PLAIN))}">""")
    if text is not None:
        doc = TextDocument.from_scene_item(text)
        width_px = rm_delta_to_css(float(text.width))
        bold_n = 0
        for run in _text_runs(doc, text.pos_y):
            p0, abs_y = run[0]
            st = p0.style.value
            bold_ord = 1
            if st == si.ParagraphStyle.BOLD:
                bold_n += 1
                bold_ord = bold_n
            left, top = html_text_origin_css(text.pos_x, abs_y, st)
            inner = _emit_run_inner([p for p, _y in run], bold_ordinal=bold_ord)
            output.write(
                f"""
                <div style="position:absolute;left:{left:.0f}px;top:{top:.0f}px;width:{width_px:.0f}px">{inner}</div>"""
            )
    output.write("""
    </body>
</html>""")
