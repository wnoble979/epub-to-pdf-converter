# epub2pdf — High-Fidelity EPUB to PDF Converter

A command-line tool that converts `.epub` files to `.pdf` with output that faithfully matches the source: all text, all images, chapter structure, and metadata. Conversion is only accepted when an automated fidelity check confirms nothing was lost.

## What it does

- Parses EPUB spine documents in reading order, extracting text, images, CSS, and table of contents
- Combines all content into a single HTML document with inlined images (base64 data URIs) and embedded CSS
- Renders the combined HTML to PDF using WeasyPrint, which provides excellent CSS/font/image fidelity
- Verifies the output against the source on three axes: text similarity (≥97%), image count, and structural outline count
- Fails loudly if verification does not pass — a conversion that silently loses content is not a conversion

## Requirements

- WSL2 Ubuntu (WeasyPrint requires Pango/Cairo/GDK-Pixbuf native libraries)
- Python 3.10+

## Installation

**1. Install system dependencies (inside WSL2):**

```bash
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev libcairo2 fonts-dejavu-core
```

**2. Create and activate a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**4. Verify the install:**

```bash
python3 -c "import weasyprint; print(weasyprint.__version__)"
```

## Usage

```bash
python3 -m epub2pdf.cli convert book.epub -o book.pdf
```

### Options

| Flag | Description |
|------|-------------|
| `-o / --output` | Output PDF path (required) |
| `--page-size A4\|LETTER` | Page size for the PDF (default: A4) |
| `--skip-verify` | Skip the post-conversion fidelity check (not recommended) |

### Examples

```bash
# Convert with default A4 page size
python3 -m epub2pdf.cli convert my-book.epub -o my-book.pdf

# Convert with US Letter page size
python3 -m epub2pdf.cli convert my-book.epub -o my-book.pdf --page-size LETTER

# Convert without fidelity check (use only if you understand the trade-off)
python3 -m epub2pdf.cli convert my-book.epub -o my-book.pdf --skip-verify
```

## The fidelity gate

After rendering, the tool automatically verifies the PDF against the source EPUB on three axes:

1. **Text similarity**: The plain text extracted from the PDF must match the source EPUB text with a SequenceMatcher ratio of at least 0.97 (97%). This catches garbled characters, missing chapters, and encoding bugs.

2. **Image count**: The number of images embedded in the PDF must exactly match the number of images *actually referenced* by `<img>`/`<image>` tags in the spine content. Note: unreferenced "orphan" images bundled in the EPUB package (alternate cover sizes, unused art) are intentionally excluded from this count, as they were never meant to render.

3. **Structural outline**: The number of PDF bookmarks must exactly match the number of TOC entries that have a content `href`. Pure grouping labels (epub `Section` nodes with no href) are excluded, since they have no corresponding heading in the content.

"Verification PASSED" means all three checks passed. Any failure prints a specific diagnostic message and exits with code 1.

## Running the test suite

```bash
python3 -m pytest -v
```

Expected: 12/12 tests passing.

## Known limitations

- **DRM-protected EPUBs**: Will fail to parse — this tool does not attempt DRM removal.
- **Embedded fonts**: Not currently carried through to the PDF. WeasyPrint would need explicit `@font-face` rules pointed at extracted font bytes.
- **Internal cross-reference links**: Links between chapters render as visible text but are not rewritten as PDF internal links.

## License

MIT — see [LICENSE](LICENSE).
