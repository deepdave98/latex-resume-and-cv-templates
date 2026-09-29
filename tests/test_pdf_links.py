"""Keep published PDF downloads and image previews reachable without the PDF viewer."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = "https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/"


class PublishedPDFLinks(unittest.TestCase):
    def test_readmes_link_directly_to_every_published_pdf(self):
        published = {path.relative_to(ROOT).as_posix() for path in (ROOT / "output/pdf").glob("*.pdf")}
        self.assertTrue(published, "No published PDFs found")
        for name in ("README.md", "output/pdf/README.md"):
            with self.subTest(document=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                links = set(re.findall(re.escape(RAW_ROOT) + r'(output/pdf/[^)"\s]+\.pdf)', text))
                self.assertEqual(links, published)
                # Relative PDF links open GitHub's embedded viewer, not the file.
                self.assertNotRegex(text, r'(?:\]\(|href=")output/pdf/[^)"\s]+\.pdf')

    def test_pdf_directory_lists_every_preview(self):
        document = ROOT / "output/pdf/README.md"
        links = re.findall(r"\]\(([^)]+\.png)\)", document.read_text(encoding="utf-8"))
        actual = {(document.parent / link).resolve() for link in links}
        expected = set()
        for pdf in (ROOT / "output/pdf").glob("*.pdf"):
            if pdf.stem == "experienced-resume":
                expected.update(ROOT / f"preview/{pdf.stem}-page-{page}.png" for page in (1, 2))
            else:
                expected.add(ROOT / f"preview/{pdf.stem}.png")
        self.assertEqual(actual, expected)
        for path in actual:
            with self.subTest(preview=path.name):
                self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
