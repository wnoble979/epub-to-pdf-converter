"""
html_normalizer.py
Combines the EPUB spine documents into a single, self-contained HTML
document suitable for WeasyPrint rendering: embeds CSS, inlines images
as base64 data URIs (so no relative-path resolution can silently break),
inserts page breaks between chapters, and tags headings with CSS
bookmark properties so WeasyPrint generates a matching PDF outline.
"""
from __future__ import annotations

import base64
import mimetypes
import warnings
from typing import Dict, Optional

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from .epub_parser import EpubDocument, resolve_image_href

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BOOKMARK_CSS = """
h1 { bookmark-level: 1; bookmark-label: content(); page-break-before: always; }
h2 { bookmark-level: 2; bookmark-label: content(); }
h3 { bookmark-level: 3; bookmark-label: content(); }
section.epub-chapter:first-of-type h1 { page-break-before: avoid; }
"""

BASE_CSS = """
@page { margin: 2cm; }
body { font-family: serif; line-height: 1.4; word-wrap: break-word; }
img { max-width: 100%; height: auto; }
"""


def _data_uri_for(src: str, images: Dict[str, bytes]) -> Optional[str]:
    href = resolve_image_href(src, images)
    if href is None:
        return None
    data = images[href]
    mime, _ = mimetypes.guess_type(href)
    mime = mime or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _inline_images(html: str, images: Dict[str, bytes]) -> str:
    # NOTE: this receives an HTML *fragment* (a chapter's body contents),
    # not a full document. bs4's "lxml" backend auto-wraps fragments in
    # <html><body>...</body></html> on parse, which would re-leak those
    # wrapper tags into the combined document. "html.parser" parses
    # fragments as fragments. (Caught while testing against a fixture.)
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        data_uri = _data_uri_for(src, images)
        if data_uri:
            img["src"] = data_uri

    # EPUB3 sometimes wraps raster images inside <svg><image xlink:href=.../></svg>
    for svg_img in soup.find_all("image"):
        href = svg_img.get("xlink:href") or svg_img.get("href")
        if not href:
            continue
        data_uri = _data_uri_for(href, images)
        if not data_uri:
            continue
        if svg_img.get("xlink:href"):
            svg_img["xlink:href"] = data_uri
        else:
            svg_img["href"] = data_uri

    return str(soup)


def build_combined_html(doc: EpubDocument) -> str:
    body_parts = []
    for _item_id, raw_html in doc.spine_html:
        soup = BeautifulSoup(raw_html, "lxml")
        body = soup.body
        inner = body.decode_contents() if body is not None else str(soup)
        inner = _inline_images(inner, doc.images)
        body_parts.append(f'<section class="epub-chapter">{inner}</section>')

    style_block = BASE_CSS + BOOKMARK_CSS + "\n".join(doc.css_blobs)

    html_doc = f"""<!DOCTYPE html>
<html lang="{doc.language}">
<head>
<meta charset="utf-8">
<title>{doc.title}</title>
<style>{style_block}</style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>"""
    return html_doc
