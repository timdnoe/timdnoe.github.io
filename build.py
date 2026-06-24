#!/usr/bin/env python3
"""Build the website (index.html) and the PDF (assets/CV.pdf) from cv.yml.

Single source of truth: cv.yml. Run `python build.py` (or let CI do it).
"""
from __future__ import annotations

import datetime
import html
import pathlib
import re

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML

ROOT = pathlib.Path(__file__).resolve().parent
CV_FILE = ROOT / "cv.yml"
TEMPLATE_DIR = ROOT / "templates"
OUT_HTML = ROOT / "index.html"
OUT_PDF = ROOT / "assets" / "CV.pdf"

_BOLD = re.compile(r"\*\*(.+?)\*\*")


def mdbold(text: str) -> Markup:
    """Escape HTML, then turn **double asterisks** into <strong>…</strong>."""
    escaped = html.escape(str(text))
    return Markup(_BOLD.sub(r"<strong>\1</strong>", escaped))


def main() -> None:
    data = yaml.safe_load(CV_FILE.read_text(encoding="utf-8")) or {}

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["mdbold"] = mdbold

    template = env.get_template("index.html.j2")
    rendered = template.render(year=datetime.date.today().year, **data)

    OUT_HTML.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(ROOT)} ({len(rendered):,} bytes)")

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    # base_url=ROOT so the print stylesheet and any images resolve from the repo root.
    HTML(string=rendered, base_url=str(ROOT)).write_pdf(str(OUT_PDF))
    print(f"wrote {OUT_PDF.relative_to(ROOT)} ({OUT_PDF.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
