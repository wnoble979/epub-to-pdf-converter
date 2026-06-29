"""
epub_parser.py
Parses an EPUB file into a structured, in-memory representation that
preserves reading order, metadata, table of contents, embedded CSS,
and embedded images. This is the single source of truth that the
fidelity verifier later compares the rendered PDF against.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import ebooklib
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import epub

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


@dataclass
class TocEntry:
    title: str
    href: str
    level: int


@dataclass
class EpubDocument:
    title: str
    author: str
    language: str
    spine_html: List[Tuple[str, str]]  # (item_id, raw_xhtml)
    spine_filenames: List[str]          # parallel list: filename for each spine item
    css_blobs: List[str]
    images: Dict[str, bytes]           # href (as stored in the epub) -> raw bytes
    toc: List[TocEntry]
    source_path: str


def _flatten_toc(nodes, level: int = 1) -> List[TocEntry]:
    flat: List[TocEntry] = []
    for node in nodes:
        if isinstance(node, tuple):
            # ebooklib represents nested sections as (Section/Link, children)
            head, children = node
            title = getattr(head, "title", None) or str(head)
            href = getattr(head, "href", "")
            flat.append(TocEntry(title=title, href=href, level=level))
            flat.extend(_flatten_toc(children, level + 1))
        else:
            title = getattr(node, "title", None) or str(node)
            href = getattr(node, "href", "")
            flat.append(TocEntry(title=title, href=href, level=level))
    return flat


def parse_epub(path: str) -> EpubDocument:
    book = epub.read_epub(path)

    title_meta = book.get_metadata("DC", "title")
    title = title_meta[0][0] if title_meta else "Untitled"

    creators = book.get_metadata("DC", "creator")
    author = creators[0][0] if creators else "Unknown"

    languages = book.get_metadata("DC", "language")
    language = languages[0][0] if languages else "en"

    spine_html: List[Tuple[str, str]] = []
    spine_filenames: List[str] = []
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        if isinstance(item, epub.EpubNav):
            # The nav document (epub3 navigation/TOC page) is spine-listed
            # by most generators but is structural, not content — including
            # it leaks the table-of-contents links into the body text.
            # (Caught by the fidelity test during development.)
            continue
        spine_html.append((item_id, item.get_content().decode("utf-8", errors="replace")))
        spine_filenames.append(item.get_name())

    css_blobs: List[str] = [
        item.get_content().decode("utf-8", errors="replace")
        for item in book.get_items_of_type(ebooklib.ITEM_STYLE)
    ]

    images: Dict[str, bytes] = {
        item.get_name(): item.get_content()
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE)
    }

    toc = _flatten_toc(book.toc)

    if not spine_html:
        raise ValueError(
            f"EPUB '{path}' has no readable spine documents — refusing to "
            f"produce a PDF that would silently drop all content."
        )

    return EpubDocument(
        title=title,
        author=author,
        language=language,
        spine_html=spine_html,
        spine_filenames=spine_filenames,
        css_blobs=css_blobs,
        images=images,
        toc=toc,
        source_path=path,
    )


def resolve_image_href(src: str, images: Dict[str, bytes]) -> Optional[str]:
    """EPUB <img> hrefs are relative to the document that references them,
    but ebooklib stores image item names relative to the OPF root. A naive
    direct-key lookup is the most common source of 'broken image' bugs, so
    fall back to a basename match. Returns the canonical key into `images`,
    or None if unresolvable."""
    if src in images:
        return src
    base = src.split("/")[-1]
    for href in images:
        if href.split("/")[-1] == base:
            return href
    return None


def referenced_image_hrefs(doc: EpubDocument) -> set:
    """The set of image hrefs actually referenced by <img>/<image> tags
    somewhere in the spine content. This — not the full set of image files
    bundled in the epub package — is the correct ground truth for fidelity
    checking: epubs routinely ship orphan/alternate image files (extra
    cover sizes, unused art) that were never meant to appear in the
    rendered output, and counting those as 'missing' produces false
    fidelity failures."""
    found = set()
    for _item_id, raw_html in doc.spine_html:
        soup = BeautifulSoup(raw_html, "lxml")
        for tag in soup.find_all(["img", "image"]):
            src = tag.get("src") or tag.get("xlink:href") or tag.get("href")
            if not src:
                continue
            resolved = resolve_image_href(src, doc.images)
            if resolved:
                found.add(resolved)
    return found


def plain_text(doc: EpubDocument) -> str:
    """Strip all markup, return concatenated plain text in reading order.
    This is the ground-truth reference the fidelity verifier diffs the
    rendered PDF's extracted text against."""
    parts = []
    for _item_id, html in doc.spine_html:
        soup = BeautifulSoup(html, "lxml")
        parts.append(soup.get_text(separator=" ", strip=True))
    return "\n".join(parts)
