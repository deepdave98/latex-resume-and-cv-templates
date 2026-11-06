#!/usr/bin/env python3
"""Compile small resumes to verify page budgets without changing the PDF."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import check_pdf_text


ROOT = Path(__file__).resolve().parents[1]
EXCEEDED = "Class resume Warning: Page limit exceeded:"
INVALID = "Class resume Warning: Invalid page limit."


def page_warnings(log):
    return [line.strip() for line in log.splitlines() if EXCEEDED in line or INVALID in line]


def document(body, preamble=""):
    return "\\documentclass{resume}\n" + preamble + "\n\\begin{document}\n" + body + "\n\\end{document}\n"


class PageLimitBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="resume-page-limits-")
        self.root = Path(self.temporary.name)
        self.count = 0

    def tearDown(self):
        self.temporary.cleanup()

    def compile(self, body, preamble="", project=None):
        if project is None:
            self.count += 1
            project = self.root / f"fixture {self.count}"
            project.mkdir()
            shutil.copyfile(ROOT / "resume.cls", project / "resume.cls")
        (project / "resume.tex").write_text(document(body, preamble), encoding="utf-8")
        # One XeLaTeX invocation: the reminder must work without a previous run.
        result = subprocess.run(
            [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"],
            cwd=project,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, "\n".join(result.stdout.splitlines()[-40:]))
        log = (project / "resume.log").read_text(encoding="utf-8", errors="replace")
        text = check_pdf_text.extract_text(project / "resume.pdf")
        return page_warnings(log), text, project

    def assert_page_count(self, text, expected):
        self.assertEqual(len(check_pdf_text.split_pages(text)), expected)

    def test_one_page_budget_accepts_one_and_warns_on_two(self):
        warnings, text, _ = self.compile("First page.", r"\resumepagelimit{1}")
        self.assertEqual(warnings, [])
        self.assert_page_count(text, 1)
        warnings, text, _ = self.compile(r"First page.\newpage Second page.", r"\resumepagelimit{1}")
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)

    def test_two_page_budget_accepts_shorter_or_exact_and_warns_on_three(self):
        for pages in (1, 2, 3):
            with self.subTest(pages=pages):
                body = r"\newpage ".join(f"Page {page}." for page in range(1, pages + 1))
                warnings, text, _ = self.compile(body, r"\resumepagelimit{2}")
                expected = [EXCEEDED + " 3 pages; limit 2."] if pages == 3 else []
                self.assertEqual(warnings, expected)
                self.assert_page_count(text, pages)

    def test_no_budget_disables_reminder(self):
        warnings, _, _ = self.compile(r"First page.\newpage Second page.\newpage Third page.")
        self.assertEqual(warnings, [])

    def test_last_valid_budget_wins(self):
        warnings, _, _ = self.compile(
            r"First page.\newpage Second page.",
            "\\resumepagelimit{1}\n\\resumepagelimit{ 2 }",
        )
        self.assertEqual(warnings, [])

    def test_invalid_values_warn_and_keep_previous_budget(self):
        # A very long number must not reach TeX's integer parser and abort.
        invalid = ("0", "-1", "1.5", "", "two", "1+1", "01", "9" * 100, r"\secretlimit")
        preamble = "\\resumepagelimit{1}\n" + "\n".join(
            "\\resumepagelimit{" + value + "}" for value in invalid
        )
        warnings, text, _ = self.compile(r"First page.\newpage Second page.", preamble)
        self.assertEqual(warnings, [INVALID] * len(invalid) + [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)

    def test_invalid_first_budget_leaves_check_disabled(self):
        warnings, _, _ = self.compile(r"First page.\newpage Second page.", r"\resumepagelimit{0}")
        self.assertEqual(warnings, [INVALID])

    def test_page_number_reset_does_not_hide_extra_page(self):
        warnings, text, _ = self.compile(
            r"First page.\clearpage\setcounter{page}{1} Second page.",
            r"\resumepagelimit{1}",
        )
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)

    def test_discarded_page_does_not_count(self):
        warnings, text, _ = self.compile(
            r"Discarded page.\newpage Retained page.",
            "\\resumepagelimit{1}\n\\AddToHookNext{shipout/before}{\\DiscardShipoutBox}",
        )
        self.assertEqual(warnings, [])
        self.assert_page_count(text, 1)
        self.assertNotIn("Discarded", text)

    def test_end_document_content_is_counted(self):
        warnings, text, _ = self.compile(
            "First page.",
            "\\resumepagelimit{1}\n\\AtEndDocument{\\newpage Second page.}",
        )
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)

    def test_shortened_rebuild_ignores_stale_aux_count(self):
        warnings, _, project = self.compile(r"First page.\newpage Second page.", r"\resumepagelimit{1}")
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        warnings, text, _ = self.compile("Only one page now.", r"\resumepagelimit{1}", project)
        self.assertEqual(warnings, [])
        self.assert_page_count(text, 1)

    def test_last_page_hook_rerun_settles_to_correct_count(self):
        preamble = "\\resumepagelimit{1}\n\\AddToHook{shipout/lastpage}{\\relax}"
        warnings, text, project = self.compile(r"First page.\newpage Second page.", preamble)
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)
        _, temporary, _ = self.compile("Only one page now.", preamble, project)
        # The kernel bypasses its shipped-page counter for this temporary page.
        # Users must resolve rerun warnings before treating the count as final.
        self.assert_page_count(temporary, 2)
        self.assertIn("Temporary page!", temporary)
        warnings, settled, _ = self.compile("Only one page now.", preamble, project)
        self.assertEqual(warnings, [])
        self.assert_page_count(settled, 1)
        self.assertNotIn("Temporary page!", settled)

    def test_check_works_without_aux_file(self):
        warnings, text, project = self.compile(
            r"First page.\newpage Second page.", "\\nofiles\n\\resumepagelimit{1}"
        )
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assert_page_count(text, 2)
        self.assertFalse((project / "resume.aux").exists())

    def test_heading_moves_to_the_next_page_with_its_first_entry(self):
        # Slide a short last section across the page foot one bullet at a time.
        entry = (
            r"\jobentry{Engineer}{Acme}{Toronto}{2024}"
            r"\begin{jobduties}\item Built a tested worker.\end{jobduties}"
        )
        for filler in range(30, 42):
            with self.subTest(filler=filler):
                body = (
                    r"\resumename{Alex Morgan}\section{Experience}"
                    + r"\begin{jobduties}" + r"\item Filler line." * filler + r"\end{jobduties}"
                    + r"\section{Projects}" + entry
                )
                _, text, _ = self.compile(body)
                for page in check_pdf_text.split_pages(text):
                    lines = [line.strip() for line in page.splitlines() if line.strip()]
                    self.assertNotEqual(lines[-1], "Projects", page)
                    if "Projects" in lines:
                        self.assertIn("Acme", page)

    def test_pages_after_the_first_show_the_name_and_page_number(self):
        body = r"\resumename{Alex Morgan}First page.\newpage Second page."
        _, text, project = self.compile(body, r"\resumepagelimit{2}")
        first, second = check_pdf_text.split_pages(text)
        self.assertNotIn("Page", first)
        self.assertIn("Alex Morgan", second.splitlines()[-1])
        self.assertTrue(second.rstrip().endswith("Page 2"))
        # The total needs the previous run's page count, as with any rerun.
        _, text, _ = self.compile(body, r"\resumepagelimit{2}", project)
        self.assertTrue(text.rstrip().endswith("Page 2 of 2"))
        _, text, _ = self.compile(r"\resumename{Alex Morgan}Only page.", r"\resumepagelimit{2}", project)
        self.assertNotIn("Page", text)

    def test_reminder_does_not_change_extracted_content(self):
        body = r"\resumename{Alex Morgan}\section{Projects}First page.\newpage Second page."
        warnings, actual, _ = self.compile(body, r"\resumepagelimit{1}")
        silent, expected, _ = self.compile(body)
        self.assertEqual(warnings, [EXCEEDED + " 2 pages; limit 1."])
        self.assertEqual(silent, [])
        self.assertEqual(actual, expected)


def main():
    missing = [name for name in ("xelatex", "pdftotext") if shutil.which(name) is None]
    if missing:
        print(
            "FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX and Poppler and add them to PATH.",
            file=sys.stderr,
        )
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PageLimitBuildTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
