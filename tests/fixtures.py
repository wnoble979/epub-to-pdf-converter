"""
fixtures.py
Builds synthetic EPUB fixtures with known, exact content so tests can
assert against ground truth rather than guessing at fuzzy similarity.
"""
import io

from ebooklib import epub
from PIL import Image

KNOWN_TEXT_CH1 = "The quick brown fox jumps over the lazy dog in chapter one."
KNOWN_TEXT_CH2 = "Chapter two contains a different, distinguishable sentence."


def make_simple_epub(path: str) -> None:
    """Two chapters, one image, a flat two-entry TOC."""
    book = epub.EpubBook()
    book.set_identifier("test-id-001")
    book.set_title("Fidelity Test Book")
    book.set_language("en")
    book.add_author("Test Author")

    img_buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(img_buf, format="JPEG")
    img_item = epub.EpubItem(
        uid="img1", file_name="images/red.jpg",
        media_type="image/jpeg", content=img_buf.getvalue(),
    )
    book.add_item(img_item)

    ch1 = epub.EpubHtml(title="Chapter 1", file_name="ch1.xhtml", lang="en")
    ch1.content = f"<h1>Chapter 1</h1><p>{KNOWN_TEXT_CH1}</p><img src='images/red.jpg'/>"

    ch2 = epub.EpubHtml(title="Chapter 2", file_name="ch2.xhtml", lang="en")
    ch2.content = f"<h1>Chapter 2</h1><p>{KNOWN_TEXT_CH2}</p>"

    book.add_item(ch1)
    book.add_item(ch2)
    book.toc = (
        epub.Link("ch1.xhtml", "Chapter 1", "ch1"),
        epub.Link("ch2.xhtml", "Chapter 2", "ch2"),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", ch1, ch2]

    epub.write_epub(path, book)


def make_multi_image_epub(path: str) -> None:
    """Three chapters, three images of different formats (one unreferenced
    — an orphan), nested TOC, and non-ASCII text — exercises the
    basename-fallback image resolver and unicode handling."""
    book = epub.EpubBook()
    book.set_identifier("test-id-002")
    book.set_title("Café Ümläut & Special Chärs")
    book.set_language("en")
    book.add_author("Author with É Accent")

    images = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        buf = io.BytesIO()
        Image.new("RGB", (50, 50), color=color).save(buf, format="PNG")
        item = epub.EpubItem(
            uid=f"img{i}", file_name=f"assets/img{i}.png",
            media_type="image/png", content=buf.getvalue(),
        )
        book.add_item(item)
        images.append(item)

    chapters = []
    texts = [
        "Naïve résumé with café — chapter A.",
        "Second chapter with an em-dash — and curly quotes “quoted”.",
        "Third chapter, final paragraph, no image here at all.",
    ]
    for i, text in enumerate(texts):
        ch = epub.EpubHtml(title=f"Section {i+1}", file_name=f"sec{i}.xhtml", lang="en")
        img_tag = f"<img src='assets/img{i}.png'/>" if i < 2 else ""
        ch.content = f"<h1>Section {i+1}</h1><p>{text}</p>{img_tag}"
        book.add_item(ch)
        chapters.append(ch)

    book.toc = (
        epub.Link("sec0.xhtml", "Section 1", "sec0"),
        (epub.Section("Part Two"), (
            epub.Link("sec1.xhtml", "Section 2", "sec1"),
            epub.Link("sec2.xhtml", "Section 3", "sec2"),
        )),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(path, book)
