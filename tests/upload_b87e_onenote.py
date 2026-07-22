#!/usr/bin/env python3
"""Export b87e fixture to InkML+HTML and upload to OneNote.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_onenote.py
  poetry run python tests/upload_b87e_onenote.py --title '…' --heading 38.5 --bold 27.5

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="")
    ap.add_argument("--heading", type=float, default=None)
    ap.add_argument("--bold", type=float, default=None)
    ap.add_argument("--second-bold", type=float, default=None)
    ap.add_argument("--plain", type=float, default=None)
    ap.add_argument("--tag", default="b87e")
    args = ap.parse_args()

    token = os.environ.get("ONENOTE_TOKEN", "")
    section = os.environ.get("ONENOTE_SECTION", "")
    email = os.environ.get("ONENOTE_EMAIL", "")
    if not token or not section:
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1

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

    h = inmkl.FONT_SIZE_PT[si.ParagraphStyle.HEADING]
    b = inmkl.FONT_SIZE_PT[si.ParagraphStyle.BOLD]
    b2 = inmkl.FONT_SIZE_SECOND_BOLD
    p = inmkl.FONT_SIZE_PT[si.ParagraphStyle.PLAIN]
    sizes = f"{h:g}/{b:g}/{b2:g}/{p:g}"
    title = args.title or f"{args.tag} fonts {sizes}"

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
