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
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from .epub_parser import EpubDocument, resolve_image_href

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BOOKMARK_CSS = """
h1 { bookmark-level: 1; bookmark-label: content(); page-break-before: always; }
h2 { bookmark-level: 2; bookmark-label: content(); }
h3 { bookmark-level: 3; bookmark-label: content(); }
section.epub-chapter:first-of-type h1 { page-break-before: avoid; }
.epub-bm-1 { bookmark-level: 1; bookmark-label: content(); page-break-before: always; }
.epub-bm-2 { bookmark-level: 2; bookmark-label: content(); }
.epub-bm-3 { bookmark-level: 3; bookmark-label: content(); }
section.epub-chapter:first-of-type .epub-bm-1 { page-break-before: avoid; }
.epub-bm-synthetic { height: 0; overflow: hidden; margin: 0; padding: 0; font-size: 0.001em; line-height: 0; }
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


_HEADING_CLASS_PREFIXES = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                           'chapter', 'title', 'head', 'part', 'section')


def _build_toc_by_file(doc: EpubDocument) -> Dict[str, List[Tuple[Optional[str], int, str]]]:
    """Group TOC entries by spine filename basename → [(fragment_or_None, level, title)]."""
    toc_by_file: Dict[str, List[Tuple[Optional[str], int, str]]] = {}
    for entry in doc.toc:
        if not entry.href:
            continue
        parts = entry.href.split('#', 1)
        basename = parts[0].split('/')[-1]
        frag = parts[1] if len(parts) > 1 else None
        toc_by_file.setdefault(basename, []).append((frag, entry.level, entry.title))
    return toc_by_file


def _inject_bookmarks(html: str, entries: List[Tuple[Optional[str], int, str]]) -> str:
    """Add epub-bm-N classes to elements targeted by TOC entries so WeasyPrint
    generates the correct PDF outline even when the EPUB uses CSS-class-based
    headings instead of semantic h1/h2/h3 tags. For image-only pages where no
    text element can be found, a synthetic invisible heading is prepended so
    the PDF outline entry is still generated."""
    soup = BeautifulSoup(html, "html.parser")
    marked: set = set()
    synthetic: List[Tuple[str, str]] = []  # (bm_class, title) for fallback entries

    for frag, level, title in entries:
        bm_class = f"epub-bm-{min(level, 3)}"

        if frag:
            anchor = soup.find(id=frag)
            if anchor is None:
                continue
            # Fragment IDs often sit on empty <a> anchors; the heading text is
            # in the parent element.
            target = anchor
            if not anchor.get_text(strip=True) and anchor.parent and anchor.parent.name:
                target = anchor.parent
        else:
            # Whole-doc entry: prefer the first element whose CSS class name
            # looks like a heading (publisher convention: .h2chap, .h3a, etc.).
            target = None
            for tag in soup.find_all(True):
                cls_list = tag.get('class', [])
                if any(c.lower().startswith(_HEADING_CLASS_PREFIXES) for c in cls_list):
                    if tag.get_text(strip=True):
                        target = tag
                        break
            # Fallback: first block element with non-trivial text.
            if target is None:
                for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    if tag.get_text(strip=True):
                        target = tag
                        break
            # Last resort: inject a synthetic zero-height heading so image-only
            # pages (e.g. covers) still get a PDF outline entry.
            if target is None:
                synthetic.append((bm_class, title))
                continue

        if target is not None:
            tid = id(target)
            if tid not in marked:
                existing = target.get('class', [])
                target['class'] = existing + [bm_class]
                marked.add(tid)

    result = str(soup)
    if synthetic:
        prefix = "".join(
            f'<p class="{cls} epub-bm-synthetic">{t}</p>'
            for cls, t in synthetic
        )
        result = prefix + result
    return result


def build_combined_html(doc: EpubDocument) -> str:
    toc_by_file = _build_toc_by_file(doc)

    body_parts = []
    for idx, (_item_id, raw_html) in enumerate(doc.spine_html):
        basename = doc.spine_filenames[idx].split('/')[-1]
        entries = toc_by_file.get(basename, [])

        soup = BeautifulSoup(raw_html, "lxml")
        body = soup.body
        inner = body.decode_contents() if body is not None else str(soup)

        if entries:
            inner = _inject_bookmarks(inner, entries)

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
