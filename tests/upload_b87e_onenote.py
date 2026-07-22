#!/usr/bin/env python3
"""Export b87e fixture to InkML+HTML and upload to OneNote.

  ONENOTE_TOKEN=… ONENOTE_SECTION=… poetry run python tests/upload_b87e_onenote.py

Never commits tokens.
"""
from __future__ import annotations

import os
import sys
from io import StringIO
from pathlib import Path

import requests
from rmscene import read_tree

from rmc.exporters.inmkl import tree_to_html, tree_to_xml

ROOT = Path(__file__).resolve().parent
RM = ROOT / "rm" / "b87e5354-9e95-4791-b5f4-672ccb94aa4e.rm"
OUT = ROOT / "onenote_calib" / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    token = os.environ.get("ONENOTE_TOKEN", "")
    section = os.environ.get("ONENOTE_SECTION", "")
    email = os.environ.get("ONENOTE_EMAIL", "")
    if not token or not section:
        print("need ONENOTE_TOKEN and ONENOTE_SECTION", file=sys.stderr)
        return 1

    with RM.open("rb") as f:
        tree = read_tree(f)

    xml_buf = StringIO()
    html_buf = StringIO()
    xml_buf.name = "b87e_style_ratio.xml"
    html_buf.name = "b87e_style_ratio.html"
    tree_to_xml(tree, xml_buf)
    tree_to_html(tree, html_buf)
    xml_path = OUT / "b87e_style_ratio.xml"
    html_path = OUT / "b87e_style_ratio.html"
    xml_path.write_text(xml_buf.getvalue(), encoding="utf-8")
    html_path.write_text(html_buf.getvalue(), encoding="utf-8")

    title = "b87e Style-ratio fonts 38.86/27.43/18/16"
    # OneNote wants title in HTML <title>
    html = html_path.read_text(encoding="utf-8")
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
    print("status", r.status_code)
    if not r.ok:
        print(r.text[:1200], file=sys.stderr)
        return 1
    page = r.json()
    print("page id:", page.get("id"))
    print("web:", page.get("links", {}).get("oneNoteWebUrl", {}).get("href"))
    print("client:", page.get("links", {}).get("oneNoteClientUrl", {}).get("href"))
    (OUT / "b87e_style_ratio_upload.json").write_text(
        __import__("json").dumps(page, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
