"""
cli.py
Command-line entry point: epub2pdf convert <input.epub> -o <output.pdf>
"""
from __future__ import annotations

import sys

import click

from .epub_parser import parse_epub
from .html_normalizer import build_combined_html
from .pdf_renderer import render_to_pdf
from .verify import verify


@click.group()
def main():
    """epub2pdf — high-fidelity EPUB to PDF converter."""


@main.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", "output_path", required=True, type=click.Path())
@click.option(
    "--page-size", default="A4",
    type=click.Choice(["A4", "LETTER"], case_sensitive=False),
)
@click.option(
    "--skip-verify", is_flag=True, default=False,
    help="Skip the post-conversion fidelity check (not recommended).",
)
def convert(input_path: str, output_path: str, page_size: str, skip_verify: bool):
    if not input_path.lower().endswith(".epub"):
        raise click.ClickException(f"'{input_path}' does not have an .epub extension.")

    click.echo(f"Parsing {input_path} ...")
    doc = parse_epub(input_path)

    click.echo(f"Building combined HTML for '{doc.title}' by {doc.author} ...")
    html_str = build_combined_html(doc)

    click.echo(f"Rendering PDF -> {output_path} ({page_size}) ...")
    render_to_pdf(html_str, output_path, page_size=page_size)

    if skip_verify:
        click.echo("Conversion complete (verification skipped).")
        return

    click.echo("Verifying fidelity ...")
    result = verify(doc, output_path)
    click.echo(f"  text similarity   : {result.text_similarity:.4f}")
    click.echo(f"  images   epub/pdf : {result.epub_image_count}/{result.pdf_image_count}")
    click.echo(f"  headings epub/pdf : {result.epub_heading_count}/{result.pdf_outline_count}")

    if not result.passed:
        for f in result.failures:
            click.echo(f"  FAIL: {f}", err=True)
        sys.exit(1)

    click.echo("Verification PASSED.")


if __name__ == "__main__":
    main()
