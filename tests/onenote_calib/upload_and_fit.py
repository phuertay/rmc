#!/usr/bin/env python3
"""Upload the calib page to OneNote and (optionally) fit scale from measurements.

Requires a Graph bearer token. Never commits tokens.

Env / args:
  ONENOTE_TOKEN   bearer token (or --token)
  ONENOTE_SECTION section id   (or --section)
  ONENOTE_EMAIL   optional /users/{email} form (or --email)

Steps:
  1. poetry run python tests/onenote_calib/generate_calib_page.py
  2. poetry run python tests/onenote_calib/upload_and_fit.py --token … --section …
  3. Open the page in OneNote: which letter (O vs H) sits on each ink cross?
  4. Record result:
       poetry run python tests/onenote_calib/upload_and_fit.py --apply ours
       # or --apply true_himetric
     That writes tests/onenote_calib/out/fit_result.json and prints the
     mapping to put in inmkl.py.

Optional quantitative fit (after you measure screenshot px of cross vs letters):
  Write out/measurements.json as:
    {"A": {"cross_css": [x,y], "winner": "O"|"H"}, …}
  then:
    poetry run python tests/onenote_calib/upload_and_fit.py --fit out/measurements.json

Readback alone cannot reveal visual px (OneNote stores ink as himetric and
HTML as CSS). The O-vs-H page is the efficient experiment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MANIFEST = OUT / "manifest.json"
FIT_RESULT = OUT / "fit_result.json"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _base(email: str) -> str:
    if email:
        return f"https://graph.microsoft.com/v1.0/users/{email}"
    return "https://graph.microsoft.com/v1.0/me"


def upload(token: str, section_id: str, email: str = "") -> dict:
    xml = OUT / "calib.xml"
    html = OUT / "calib.html"
    if not xml.is_file() or not html.is_file():
        sys.exit("missing calib.xml/html — run generate_calib_page.py first")
    url = f"{_base(email)}/onenote/sections/{section_id}/pages"
    with xml.open("rb") as xf, html.open("rb") as hf:
        files = {
            "presentation-onenote-inkml": (xml.name, xf, "application/inkml+xml"),
            "presentation": (html.name, hf, "text/html"),
        }
        r = requests.post(url, headers=_headers(token), files=files, timeout=120)
    if not r.ok:
        sys.exit(f"upload failed {r.status_code}: {r.text[:800]}")
    page = r.json()
    (OUT / "upload_response.json").write_text(json.dumps(page, indent=2), encoding="utf-8")
    print("uploaded page id:", page.get("id"))
    print("client URL:", page.get("links", {}).get("oneNoteClientUrl", {}).get("href"))
    print("web URL:   ", page.get("links", {}).get("oneNoteWebUrl", {}).get("href"))
    return page


def readback(token: str, page_id: str, email: str = "") -> None:
    """Save HTML + InkML as returned by OneNote (coordinates, not visual px)."""
    url = f"{_base(email)}/onenote/pages/{page_id}/content?includeInkML=true"
    r = requests.get(url, headers={**_headers(token), "Accept": "*/*"}, timeout=120)
    if not r.ok:
        sys.exit(f"readback failed {r.status_code}: {r.text[:800]}")
    ctype = r.headers.get("content-type", "")
    raw = OUT / "readback_raw.bin"
    raw.write_bytes(r.content)
    print(f"wrote {raw} ({len(r.content)} bytes, {ctype})")
    # Best-effort multipart split
    if "multipart" in ctype and "boundary=" in ctype:
        boundary = ctype.split("boundary=", 1)[1].strip().strip('"')
        parts = r.content.split(f"--{boundary}".encode())
        n = 0
        for part in parts:
            if b"application/inkml" in part[:400].lower() or b"inkml+xml" in part[:400].lower():
                body = part.split(b"\r\n\r\n", 1)[-1].rstrip(b"\r\n--")
                (OUT / "readback.xml").write_bytes(body)
                n += 1
            elif b"text/html" in part[:400].lower():
                body = part.split(b"\r\n\r\n", 1)[-1].rstrip(b"\r\n--")
                (OUT / "readback.html").write_bytes(body)
                n += 1
        print(f"split {n} multipart parts → readback.xml / readback.html")
    else:
        # Sometimes HTML only
        (OUT / "readback.html").write_bytes(r.content)
        print("non-multipart body saved as readback.html")


def apply_winner(winner: str) -> dict:
    """Record which hypothesis won and the mapping to use in inmkl.py."""
    if not MANIFEST.is_file():
        sys.exit("missing manifest.json — generate first")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if winner == "ours":
        result = {
            "winner": "ours",
            "css_from_inkml": "inkml / RM_PER_INK",
            "rm_per_ink": man["rm_per_ink"],
            "note": "Keep current cancel-CONV mapping (scale_to_css_px = /10).",
            "action": "no inmkl change for scale; investigate anchors/title offset next",
        }
    elif winner == "true_himetric":
        result = {
            "winner": "true_himetric",
            "css_from_inkml": "inkml * 96 / 2540",
            "rm_to_inkml": f"rm * ({man['rm_to_true_himetric']:.6f}) + pad",
            "note": "Switch rm_to_inkml to physical himetric and css = himetric*96/2540.",
            "action": "patch inmkl.RM_PER_INK → 2540/226 and inkml_to_css → *96/2540",
            "suggested_constants": {
                "RM_PER_INK": man["rm_to_true_himetric"],
                "inkml_to_css_factor": 96 / 2540,
            },
        }
    else:
        sys.exit("--apply must be 'ours' or 'true_himetric'")
    FIT_RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {FIT_RESULT}")
    return result


def fit_measurements(path: Path) -> dict:
    """Fit CSS = inkml / K from measured cross positions vs marker CSS."""
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    meas = json.loads(path.read_text(encoding="utf-8"))
    # Each entry: label -> {winner: O|H} or {cross_css: [x,y]}
    winners = []
    ratios = []
    for m in man["markers"]:
        lab = m["label"]
        if lab not in meas:
            continue
        entry = meas[lab]
        if "winner" in entry:
            winners.append(entry["winner"].upper().replace("O", "ours").replace("H", "true_himetric"))
        if "cross_css" in entry:
            cx, cy = entry["cross_css"]
            ix, iy = m["inkml"]
            if cx:
                ratios.append(ix / cx)
            if cy:
                ratios.append(iy / cy)
    result = {"winners": winners, "inkml_per_css_samples": ratios}
    if ratios:
        k = sum(ratios) / len(ratios)
        result["fitted_inkml_per_css"] = k
        result["fitted_css_from_inkml"] = f"inkml / {k:.4f}"
        result["compare_ours"] = man["rm_per_ink"]
        result["compare_true"] = man["true_himetric_per_css_px"]
    if winners:
        # majority
        ours = sum(1 for w in winners if "ours" in w or w == "O")
        true = sum(1 for w in winners if "true" in w or w == "H")
        result["majority"] = "ours" if ours >= true else "true_himetric"
    FIT_RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--token", default=os.environ.get("ONENOTE_TOKEN", ""))
    p.add_argument("--section", default=os.environ.get("ONENOTE_SECTION", ""))
    p.add_argument("--email", default=os.environ.get("ONENOTE_EMAIL", ""))
    p.add_argument("--page-id", default="", help="existing page id for readback only")
    p.add_argument("--upload", action="store_true")
    p.add_argument("--readback", action="store_true")
    p.add_argument("--apply", choices=["ours", "true_himetric"], help="record visual winner")
    p.add_argument("--fit", type=Path, help="measurements.json for quantitative fit")
    p.add_argument("--generate", action="store_true", help="run generate_calib_page first")
    args = p.parse_args()

    if args.generate or not (OUT / "calib.xml").is_file():
        import importlib.util

        gen_path = ROOT / "generate_calib_page.py"
        spec = importlib.util.spec_from_file_location("generate_calib_page", gen_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        mod.generate()

    if args.apply:
        apply_winner(args.apply)
        return
    if args.fit:
        fit_measurements(args.fit)
        return

    if not args.upload and not args.readback:
        # default: upload + print next steps
        args.upload = True

    if args.upload:
        if not args.token or not args.section:
            sys.exit("need --token and --section (or ONENOTE_TOKEN / ONENOTE_SECTION)")
        page = upload(args.token, args.section, args.email)
        args.page_id = page.get("id", args.page_id)
        print(
            "\nNext: open the page in OneNote. For crosses A–D, note whether "
            "red O or blue H sits on the ink. Then run:\n"
            "  poetry run python tests/onenote_calib/upload_and_fit.py --apply ours\n"
            "  # or --apply true_himetric\n"
        )

    if args.readback:
        if not args.token or not args.page_id:
            sys.exit("readback needs --token and --page-id")
        readback(args.token, args.page_id, args.email)


if __name__ == "__main__":
    main()
