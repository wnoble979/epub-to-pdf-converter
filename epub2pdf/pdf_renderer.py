"""
pdf_renderer.py
Renders the combined HTML document to a PDF file using WeasyPrint.
"""
from __future__ import annotations

from weasyprint import CSS, HTML

PAGE_SIZES = {
    "A4": "@page { size: A4; }",
    "LETTER": "@page { size: letter; }",
}


def render_to_pdf(html_str: str, output_path: str, page_size: str = "A4") -> None:
    page_css = PAGE_SIZES.get(page_size.upper(), PAGE_SIZES["A4"])
    HTML(string=html_str).write_pdf(
        output_path,
        stylesheets=[CSS(string=page_css)],
    )
