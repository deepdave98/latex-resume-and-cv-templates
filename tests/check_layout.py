#!/usr/bin/env python3
"""Compile realistic entry lengths and check text bounds on Letter and A4."""

from collections import Counter
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import check_pdf_text


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("Short employer", "Northstar", "Toronto", "2022 -- Present"),
    ("Long university", "Northern Institute of Computer Science and Applied Engineering", "Vancouver, British Columbia", "September 2019 -- December 2023"),
    ("Long employer", "Regional Transportation Software and Infrastructure Cooperative", "San Francisco Bay Area, California", "January 2022 -- Present"),
    ("No location", "Open Source Developer Tools and Distributed Systems Project", "", "2023 -- Present"),
    ("Long dates", "Northstar Infrastructure", "Toronto", "September 2019 -- December 2021; January 2023 -- Present"),
    ("Both columns wrap", "Regional Transportation Software and Infrastructure Cooperative", "San Francisco Bay Area, California", "September 2019 -- December 2021; January 2023 -- Present"),
    ("No dates", "Northern Institute of Computer Science and Applied Engineering", "Vancouver, British Columbia", ""),
    ("No dates with wrapping", "Northern Institute of Computer Science and Applied Engineering Research and Development Cooperative", "Vancouver, British Columbia", ""),
)


def document(body, paper):
    return "\\documentclass[" + paper + "]{resume}\n\\begin{document}\n" + body + "\n\\end{document}\n"


class EntryLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="resume-layout-")
        self.root = Path(self.temporary.name)
        self.count = 0

    def tearDown(self):
        self.temporary.cleanup()

    def compile(self, body, paper):
        self.count += 1
        project = self.root / f"fixture {self.count}"
        project.mkdir()
        shutil.copyfile(ROOT / "resume.cls", project / "resume.cls")
        (project / "resume.tex").write_text(document(body, paper), encoding="utf-8")
        result = subprocess.run(
            [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"],
            cwd=project, capture_output=True, encoding="utf-8", errors="replace", timeout=120,
        )
        self.assertEqual(result.returncode, 0, "\n".join(result.stdout.splitlines()[-35:]))
        log = (project / "resume.log").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("Overfull ", log)
        pdf = project / "resume.pdf"
        text = check_pdf_text.extract_text(pdf)
        bounds = subprocess.run(
            [shutil.which("pdftotext"), "-bbox", str(pdf), "-"],
            check=True, capture_output=True, encoding="utf-8", timeout=30,
        )
        return text, ET.fromstring(bounds.stdout)

    def assert_inside_margins(self, tree):
        for number, page in enumerate(tree.findall(".//{*}page"), start=1):
            width, height = float(page.attrib["width"]), float(page.attrib["height"])
            words = page.findall(".//{*}word")
            self.assertTrue(words)
            for word in words:
                y_min, y_max = float(word.attrib["yMin"]), float(word.attrib["yMax"])
                self.assertGreaterEqual(float(word.attrib["xMin"]), 35.5, word.text)
                self.assertLessEqual(float(word.attrib["xMax"]), width - 35.5, word.text)
                if number > 1 and y_min > height - 35.5:
                    continue  # the class prints the name and page number in the bottom margin
                # The 30pt name glyph rises above the body margin.
                top = 31.5 if y_max - y_min > 25 and y_max < 65 else 35.5
                self.assertGreaterEqual(y_min, top, word.text)
                self.assertLessEqual(y_max, height - 35.5, word.text)
            for index, word in enumerate(words):
                for other in words[index + 1:]:
                    x_overlap = min(float(word.attrib["xMax"]), float(other.attrib["xMax"])) - max(float(word.attrib["xMin"]), float(other.attrib["xMin"]))
                    y_overlap = min(float(word.attrib["yMax"]), float(other.attrib["yMax"])) - max(float(word.attrib["yMin"]), float(other.attrib["yMin"]))
                    self.assertFalse(x_overlap > 0.5 and y_overlap > 0.5, (word.text, other.text))

    def test_entry_lengths_on_both_paper_sizes(self):
        for paper in ("letterpaper", "a4paper"):
            for role, organization, location, dates in CASES:
                with self.subTest(paper=paper, role=role):
                    body = "\\jobentry{" + role + "}{" + organization + "}{" + location + "}{" + dates + "}"
                    text, tree = self.compile(body, paper)
                    self.assertEqual(len(check_pdf_text.split_pages(text)), 1)
                    # Layout extraction may interleave wrapped columns. Require
                    # every word exactly once; visual bounds are checked separately.
                    expected = " ".join((organization, "--" if location else "", location, dates, role)).replace("--", "–")
                    self.assertEqual(Counter(check_pdf_text.words(text)), Counter(check_pdf_text.words(expected)))
                    self.assertTrue(text.strip().endswith(role), text)
                    self.assert_inside_margins(tree)
                    if dates:
                        # Font sizes differ, but the first company/date lines
                        # must start together, not one text line apart.
                        pdf_words = tree.findall(".//{*}word")
                        organization_word = next(word for word in pdf_words if word.text == organization.split()[0])
                        date_word = next(word for word in pdf_words if word.text == dates.split()[0])
                        self.assertLess(abs(float(organization_word.attrib["yMin"]) - float(date_word.attrib["yMin"])), 2)

    def test_long_rows_wrap_beside_their_dates(self):
        body = r"""\resumerow{Short Certification}{Issuer}{2024}
\resumerow{A certification with a very long name that must wrap beside its date column, Professional}{Some Very Long Issuing Organization Name}{January 2022 -- January 2025}
\resumerow{Honors List}{Lakeshore University}{}"""
        for paper in ("letterpaper", "a4paper"):
            with self.subTest(paper=paper):
                text, tree = self.compile(body, paper)
                self.assertEqual(len(check_pdf_text.split_pages(text)), 1)
                for phrase in ("Short Certification – Issuer", "Professional", "January 2025", "Honors List – Lakeshore University"):
                    self.assertIn(phrase, text)
                self.assert_inside_margins(tree)

    def test_long_contact_line_wraps_after_a_separator(self):
        body = r"""\resumename{Alex Morgan}
\resumecontact{Toronto, Ontario, Canada
  \contactsep \resumephone{+1 (416) 555-0123}
  \contactsep \resumeemail{alexandra.morgan-anderson@example.com}
  \contactsep \resumelink{https://www.linkedin.com/in/alexandra-morgan-anderson}{linkedin.com/in/alexandra-morgan-anderson}
  \contactsep \resumelink{https://github.com/alexandra-morgan-anderson}{github.com/alexandra-morgan-anderson}}"""
        for paper in ("letterpaper", "a4paper"):
            with self.subTest(paper=paper):
                text, tree = self.compile(body, paper)
                contact = [line.strip() for line in text.splitlines() if "⋄" in line]
                self.assertEqual(len(contact), 2, text)
                self.assertTrue(contact[0].endswith("⋄"), contact[0])
                self.assertFalse(contact[1].startswith("⋄"), contact[1])
                self.assert_inside_margins(tree)

    def test_promotion_titles_and_dates_wrap_without_losing_text(self):
        title = "Senior Software Engineer, Infrastructure Reliability and Developer Productivity"
        dates = "September 2020 -- December 2022; January 2024 -- Present"
        body = r"\jobsubentry{" + title + "}{" + dates + "}"
        for paper in ("letterpaper", "a4paper"):
            with self.subTest(paper=paper):
                text, tree = self.compile(body, paper)
                self.assertEqual(len(check_pdf_text.split_pages(text)), 1)
                expected = (title + " " + dates).replace("--", "–")
                self.assertEqual(Counter(check_pdf_text.words(text)), Counter(check_pdf_text.words(expected)))
                self.assert_inside_margins(tree)

    def test_wrapped_promotion_stays_with_its_first_bullet_near_page_end(self):
        for paper, space in (("letterpaper", "9.3in"), ("a4paper", "10in")):
            with self.subTest(paper=paper):
                body = r"First page marker\par\vspace*{" + space + "}\n" + r"""
\jobsubentry{Senior Software Engineer, Infrastructure Reliability and Developer Productivity}{September 2020 -- December 2022; January 2024 -- Present}
\begin{jobduties}
\item Maintained the deployment service.
\end{jobduties}
"""
                text, tree = self.compile(body, paper)
                pages = check_pdf_text.split_pages(text)
                self.assertEqual(len(pages), 2)
                self.assertNotIn("Senior", pages[0])
                for word in ("Senior", "Productivity", "Present", "Maintained"):
                    self.assertIn(word, pages[1])
                self.assert_inside_margins(tree)

    def test_heading_and_role_move_together_near_page_end(self):
        for paper, remaining in (("letterpaper", "9.3in"), ("a4paper", "10in")):
            with self.subTest(paper=paper):
                body = r"First page marker\par\vspace*{" + remaining + r"}" + "\n" + r"""
\jobentry{Platform engineer}{Regional Transportation Software and Infrastructure Cooperative}{San Francisco Bay Area, California}{January 2022 -- Present}
\begin{jobduties}
\item Maintained the deployment service.
\end{jobduties}
"""
                text, tree = self.compile(body, paper)
                pages = check_pdf_text.split_pages(text)
                self.assertEqual(len(pages), 2)
                self.assertNotIn("Cooperative", pages[0])
                self.assertIn("Cooperative", pages[1])
                self.assertIn("Platform engineer", pages[1])
                self.assert_inside_margins(tree)


def main():
    missing = [name for name in ("xelatex", "pdftotext") if shutil.which(name) is None]
    if missing:
        print("FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX and Poppler and add them to PATH.", file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EntryLayoutTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
