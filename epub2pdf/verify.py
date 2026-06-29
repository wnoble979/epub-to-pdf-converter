"""
verify.py
Post-conversion fidelity verification. Compares the generated PDF against
the source EPUB on three axes: text content, image count, and structural
(heading/bookmark) count. This is the gate that decides whether a
conversion is accepted — a failure here means a real bug, not a warning
to be ignored.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF
from pypdf import PdfReader

from .epub_parser import EpubDocument, plain_text, referenced_image_hrefs

TEXT_SIMILARITY_THRESHOLD = 0.97
IMAGE_COUNT_TOLERANCE = 0
STRUCTURE_COUNT_TOLERANCE = 0


@dataclass
class VerificationResult:
    passed: bool
    text_similarity: float
    epub_image_count: int
    pdf_image_count: int
    epub_heading_count: int
    pdf_outline_count: int
    failures: List[str]


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _pdf_plain_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def _pdf_image_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    try:
        seen = set()
        for page in doc:
            for img in page.get_images(full=True):
                seen.add(img[0])  # xref id — dedupe images reused across pages
        return len(seen)
    finally:
        doc.close()


def _count_outline_entries(items) -> int:
    total = 0
    for item in items:
        if isinstance(item, list):
            total += _count_outline_entries(item)
        else:
            total += 1
    return total


def _pdf_outline_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    try:
        return _count_outline_entries(reader.outline)
    except Exception:
        return 0


def verify(epub_doc: EpubDocument, pdf_path: str) -> VerificationResult:
    failures: List[str] = []

    source_text = plain_text(epub_doc)
    rendered_text = _pdf_plain_text(pdf_path)
    similarity = difflib.SequenceMatcher(
        a=_normalize(source_text), b=_normalize(rendered_text)
    ).ratio()
    if similarity < TEXT_SIMILARITY_THRESHOLD:
        failures.append(
            f"Text fidelity {similarity:.4f} is below the "
            f"{TEXT_SIMILARITY_THRESHOLD} threshold — content was lost or "
            f"corrupted during rendering."
        )

    epub_images = len(referenced_image_hrefs(epub_doc))
    pdf_images = _pdf_image_count(pdf_path)
    if abs(epub_images - pdf_images) > IMAGE_COUNT_TOLERANCE:
        failures.append(
            f"Image count mismatch: epub content references {epub_images} "
            f"distinct images, PDF contains {pdf_images}. Likely an "
            f"unresolved image href in html_normalizer.resolve_image_href."
        )

    epub_headings = len([e for e in epub_doc.toc if e.href])
    pdf_outline = _pdf_outline_count(pdf_path)
    if epub_headings and abs(epub_headings - pdf_outline) > STRUCTURE_COUNT_TOLERANCE:
        failures.append(
            f"Structure mismatch: epub TOC has {epub_headings} content-linked "
            f"entries, PDF outline has {pdf_outline} bookmarks."
        )

    return VerificationResult(
        passed=not failures,
        text_similarity=similarity,
        epub_image_count=epub_images,
        pdf_image_count=pdf_images,
        epub_heading_count=epub_headings,
        pdf_outline_count=pdf_outline,
        failures=failures,
    )
