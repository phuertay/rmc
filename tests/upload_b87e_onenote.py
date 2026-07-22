#!/usr/bin/env python3
"""Export b87e fixture to InkML+HTML and upload to OneNote.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_onenote.py
  poetry run python tests/upload_b87e_onenote.py --title '…' --heading 38.5 --bold 27.5

Caches token to /tmp/onenote_token.env (mode 600); reuses before asking again.
Never commits tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from io import StringIO
from pathlib import Path

import requests
from rmscene import read_tree
from rmscene import scene_items as si

from rmc.exporters import inmkl
from rmc.exporters.inmkl import tree_to_html, tree_to_xml

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"
OUT = ROOT / "onenote_calib" / "out"
OUT.mkdir(parents=True, exist_ok=True)
TOKEN_CACHE = Path("/tmp/onenote_token.env")


def _load_token_cache() -> None:
    """Reuse last Graph token from /tmp before asking for a new one."""
    if os.environ.get("ONENOTE_TOKEN") and os.environ.get("ONENOTE_SECTION"):
        return
    if not TOKEN_CACHE.is_file():
        return
    for line in TOKEN_CACHE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("export "):
            continue
        # export NAME='value'  or  export NAME=value
        _, _, rest = line.partition(" ")
        name, _, raw = rest.partition("=")
        if name not in ("ONENOTE_TOKEN", "ONENOTE_SECTION", "ONENOTE_EMAIL"):
            continue
        if os.environ.get(name):
            continue
        val = raw.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        os.environ[name] = val


def _save_token_cache(token: str, section: str, email: str = "") -> None:
    lines = [
        f"export ONENOTE_TOKEN='{token}'",
        f"export ONENOTE_SECTION='{section}'",
    ]
    if email:
        lines.append(f"export ONENOTE_EMAIL='{email}'")
    TOKEN_CACHE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        TOKEN_CACHE.chmod(0o600)
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="")
    ap.add_argument("--heading", type=float, default=None)
    ap.add_argument("--bold", type=float, default=None)
    ap.add_argument("--second-bold", type=float, default=None)
    ap.add_argument("--plain", type=float, default=None)
    ap.add_argument("--ink-scale", type=float, default=None, help="page-wide INK_SCALE")
    ap.add_argument(
        "--l2-text-dy",
        type=float,
        default=None,
        help="first-BOLD HTML top nudge CSS px (+ lowers text)",
    )
    ap.add_argument("--tag", default="b87e")
    args = ap.parse_args()

    _load_token_cache()
    token = os.environ.get("ONENOTE_TOKEN", "")
    section = os.environ.get("ONENOTE_SECTION", "")
    email = os.environ.get("ONENOTE_EMAIL", "")
    if not token or not section:
        print("need ONENOTE_TOKEN and ONENOTE_SECTION (no /tmp cache)", file=sys.stderr)
        return 1
    _save_token_cache(token, section, email)

    if args.ink_scale is not None:
        inmkl.INK_SCALE = args.ink_scale
        inmkl.WIDTH_CONV_CONSTANT = inmkl.RM_PER_INK * args.ink_scale
        inmkl.HEIGHT_CONV_CONSTANT = inmkl.RM_PER_INK * args.ink_scale
    if args.heading is not None:
        inmkl.FONT_SIZE_PT[si.ParagraphStyle.HEADING] = args.heading
    if args.bold is not None:
        inmkl.FONT_SIZE_PT[si.ParagraphStyle.BOLD] = args.bold
    if args.plain is not None:
        inmkl.FONT_SIZE_PT[si.ParagraphStyle.PLAIN] = args.plain
        for st in (
            si.ParagraphStyle.BULLET,
            si.ParagraphStyle.BULLET2,
            si.ParagraphStyle.CHECKBOX,
            si.ParagraphStyle.CHECKBOX_CHECKED,
        ):
            inmkl.FONT_SIZE_PT[st] = args.plain
    if args.second_bold is not None:
        inmkl.FONT_SIZE_SECOND_BOLD = args.second_bold
    if args.l2_text_dy is not None:
        inmkl.TEXT_NUDGE_DY_BOLD1_CSS = args.l2_text_dy

    h = inmkl.FONT_SIZE_PT[si.ParagraphStyle.HEADING]
    b = inmkl.FONT_SIZE_PT[si.ParagraphStyle.BOLD]
    b2 = inmkl.FONT_SIZE_SECOND_BOLD
    p = inmkl.FONT_SIZE_PT[si.ParagraphStyle.PLAIN]
    sizes = f"{h:g}/{b:g}/{b2:g}/{p:g}"
    S = inmkl.INK_SCALE
    l2dy = inmkl.TEXT_NUDGE_DY_BOLD1_CSS
    title = args.title or f"{args.tag} S{S:g} fonts {sizes} L2dy{l2dy:g}"

    with RM.open("rb") as f:
        tree = read_tree(f)

    stem = args.tag.replace(" ", "_")
    xml_buf = StringIO()
    html_buf = StringIO()
    xml_buf.name = f"{stem}.xml"
    html_buf.name = f"{stem}.html"
    tree_to_xml(tree, xml_buf)
    tree_to_html(tree, html_buf)
    xml_path = OUT / f"{stem}.xml"
    html_path = OUT / f"{stem}.html"
    xml_path.write_text(xml_buf.getvalue(), encoding="utf-8")
    html = html_buf.getvalue()
    if "<title>" not in html.lower():
        html = f"<html><head><title>{title}</title></head><body>{html}</body></html>"
    else:
        # force page title OneNote shows in notebook list
        import re

        html = re.sub(
            r"(?is)<title>.*?</title>",
            f"<title>{title}</title>",
            html,
            count=1,
        )
        if "<title>" not in html.lower():
            html = f"<html><head><title>{title}</title></head><body>{html}</body></html>"
    html_path.write_text(html, encoding="utf-8")

    base = (
        f"https://graph.microsoft.com/v1.0/users/{email}"
        if email
        else "https://graph.microsoft.com/v1.0/me"
    )
    url = f"{base}/onenote/sections/{section}/pages"
    with xml_path.open("rb") as xf, html_path.open("rb") as hf:
        files = {
            "presentation-onenote-inkml": (xml_path.name, xf, "application/inkml+xml"),
            "presentation": (html_path.name, hf, "text/html"),
        }
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=120,
        )
    print("title:", title)
    print("status", r.status_code)
    if not r.ok:
        print(r.text[:1200], file=sys.stderr)
        return 1
    page = r.json()
    print("page id:", page.get("id"))
    print("web:", page.get("links", {}).get("oneNoteWebUrl", {}).get("href"))
    print("client:", page.get("links", {}).get("oneNoteClientUrl", {}).get("href"))
    (OUT / f"{stem}_upload.json").write_text(json.dumps(page, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
