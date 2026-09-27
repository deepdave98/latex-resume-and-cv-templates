#!/usr/bin/env python3
"""Compile the admissions CV and its optional sections on Letter and A4."""

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import check_contacts
import check_pdf_text
import check_placeholders


ROOT = Path(__file__).resolve().parents[1]
PAPERS = {"letterpaper": (612, 792), "a4paper": (595.276, 841.89)}
CONTACTS = [
    "mailto:hello@example.com", "https://example.com", "https://github.com/your-handle",
]


class AdmissionsTemplateTests(unittest.TestCase):
    def source(self, paper):
        source = (ROOT / "templates/graduate-admissions-resume.tex").read_text(encoding="utf-8")
        self.assertEqual(source.count(r"\documentclass{resume}"), 1)
        return source.replace(r"\documentclass{resume}", "\\documentclass[" + paper + "]{resume}")

    def enable(self, source, block):
        pattern = rf"(% BEGIN OPTIONAL {block}\n)(.*?)(% END OPTIONAL {block})"
        matches = list(re.finditer(pattern, source, re.S))
        self.assertEqual(len(matches), 1)
        match = matches[0]
        lines = match[2].splitlines(keepends=True)
        self.assertTrue(all(line.startswith("% ") for line in lines))
        return source[:match.start(2)] + "".join(line[2:] for line in lines) + source[match.end(2):]

    def assert_bounds(self, pdf, paper, page_count):
        result = subprocess.run(
            [shutil.which("pdftotext"), "-bbox", str(pdf), "-"],
            check=True, capture_output=True, encoding="utf-8", timeout=30,
        )
        pages = ET.fromstring(result.stdout).findall(".//{*}page")
        self.assertEqual(len(pages), page_count)
        width, height = PAPERS[paper]
        for page in pages:
            self.assertAlmostEqual(float(page.attrib["width"]), width, delta=0.1)
            self.assertAlmostEqual(float(page.attrib["height"]), height, delta=0.1)
            boxes = []
            for word in page.findall(".//{*}word"):
                x1, y1, x2, y2 = (float(word.attrib[key]) for key in ("xMin", "yMin", "xMax", "yMax"))
                # Preserve the shared class's large name glyph above the body margin.
                top = 31.5 if y2 - y1 > 25 and y2 < 65 else 35.5
                self.assertTrue(35.5 <= x1 < x2 <= width - 35.5, word.text)
                self.assertTrue(top <= y1 < y2 <= height - 35.5, word.text)
                for other in boxes:
                    self.assertFalse(
                        min(x2, other[2]) - max(x1, other[0]) > 0.5
                        and min(y2, other[3]) - max(y1, other[1]) > 0.5,
                        f"Overlapping words: {word.text}, {other[4]}",
                    )
                boxes.append((x1, y1, x2, y2, word.text))
            self.assertTrue(boxes, "Empty page")

    def compile(self, source, paper, pages=1):
        with tempfile.TemporaryDirectory(prefix="resume-admissions-") as temporary:
            project = Path(temporary) / "project with spaces"
            project.mkdir()
            shutil.copyfile(ROOT / "resume.cls", project / "resume.cls")
            (project / "resume.tex").write_text(source, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("latexmk"), "-xelatex", "-interaction=nonstopmode",
                 "-halt-on-error", "-file-line-error", "resume.tex"],
                cwd=project, capture_output=True, encoding="utf-8", errors="replace", timeout=180,
            )
            self.assertEqual(result.returncode, 0, "\n".join(result.stdout.splitlines()[-40:]))
            log = (project / "resume.log").read_text(encoding="utf-8")
            self.assertNotIn("Overfull ", log)
            self.assertNotIn("Page limit exceeded", log)
            pdf = project / "resume.pdf"
            text = check_pdf_text.extract_text(pdf)
            extracted_pages = check_pdf_text.split_pages(text)
            self.assertEqual(len(extracted_pages), pages)
            self.assertTrue(all(page.strip() for page in extracted_pages))
            self.assert_bounds(pdf, paper, pages)
            self.assertEqual(check_contacts.extract_urls(pdf), CONTACTS)
            return text, log

    def test_default_cv_and_placeholder_warnings(self):
        for paper in PAPERS:
            with self.subTest(paper=paper):
                text, log = self.compile(self.source(paper), paper)
                headings = [text.index(title) for title in (
                    "Education", "Research Experience", "Selected Academic Project",
                    "Teaching and Service", "Research Skills",
                )]
                self.assertEqual(headings, sorted(headings))
                for omitted in ("Publications", "Preprints", "Presentations"):
                    self.assertNotIn(omitted, text)
                reminders = check_placeholders.reminders(log)
                for field in ("resume name.", "contact details.", "entry 1 bullets.", "skills bullets."):
                    self.assertIn(field, reminders)

    def test_each_optional_block_compiles(self):
        for paper in PAPERS:
            for block, title, status in (
                ("PUBLICATIONS", "Publications", "[Published / accepted]"),
                ("PREPRINTS", "Preprints", "not peer reviewed"),
                ("PRESENTATIONS", "Presentations", "Poster presented at"),
            ):
                with self.subTest(paper=paper, block=block):
                    text, log = self.compile(self.enable(self.source(paper), block), paper)
                    self.assertEqual(text.count(title), 1)
                    self.assertIn(status, text)
                    if block != "PRESENTATIONS":
                        self.assertIn("[Authors in order]", text)
                    self.assertTrue(check_placeholders.reminders(log))

    def test_two_degrees_and_outputs_allow_a_second_page(self):
        for paper in PAPERS:
            with self.subTest(paper=paper):
                source = self.source(paper).replace(r"\resumepagelimit{1}", r"\resumepagelimit{2}")
                degree = r"""
\jobentry{[Master's Degree in Field]}{[Graduate University]}{}{Expected [Month Year]}
\begin{jobduties}
  \item Thesis: [Graduate thesis title]. Supervisor: [Name]. In progress.
\end{jobduties}
"""
                source = source.replace(r"\section{Education}", r"\section{Education}" + degree)
                for block in ("PUBLICATIONS", "PREPRINTS", "PRESENTATIONS"):
                    source = self.enable(source, block)
                text, _ = self.compile(source, paper, pages=2)
                self.assertLess(text.index("[Graduate University]"), text.index("[University]"))
                for title in ("Publications", "Preprints", "Presentations"):
                    self.assertEqual(text.count(title), 1)
                teaching_page = next(page for page in check_pdf_text.split_pages(text)
                                     if "Teaching and Service" in page)
                self.assertIn("[Department or Organization]", teaching_page)
                self.assertIn("Led [tutorial or activity]", teaching_page)

    def test_project_first_adaptation_without_research_or_teaching(self):
        for paper in PAPERS:
            with self.subTest(paper=paper):
                source = self.source(paper)
                before, rest = source.split(r"\section{Research Experience}", 1)
                _, after = rest.split(r"\section{Selected Academic Project}", 1)
                source = before + r"\section{Selected Academic Project}" + after
                before, rest = source.split(r"\section{Teaching and Service}", 1)
                _, after = rest.split(r"\section{Research Skills}", 1)
                source = before + r"\section{Skills}" + after
                source = re.sub(r"^  \\item Thesis:.*\n", "", source, flags=re.M)
                text, _ = self.compile(source, paper)
                for omitted in ("Thesis:", "Research Experience", "Teaching and Service"):
                    self.assertNotIn(omitted, text)
                self.assertLess(text.index("Education"), text.index("Selected Academic Project"))
                self.assertIn("[Course Project / Independent Study]", text)


def main():
    missing = [name for name in ("latexmk", "xelatex", "pdftotext", "pdfinfo") if shutil.which(name) is None]
    if missing:
        print("FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX, latexmk, and Poppler.", file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionsTemplateTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
