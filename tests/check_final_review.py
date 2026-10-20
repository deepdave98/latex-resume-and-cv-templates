#!/usr/bin/env python3
"""Exercise the one-source review command with real TeX and Poppler builds."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_application_versions
import check_pdf_text
import check_starter_builds


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_resume
import package_application_versions
import review_resume


def published_files():
    return {
        str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
        for folder in ("output/pdf", "preview", "downloads")
        for path in (ROOT / folder).rglob("*") if path.is_file()
    }


class FinalReviewBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="final review tests ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        shutil.copyfile(ROOT / "resume.cls", self.root / "resume.cls")

    def run_review(self, source, *options):
        out, err = StringIO(), StringIO()
        with patch.object(review_resume, "ROOT", self.root):
            with redirect_stdout(out), redirect_stderr(err):
                code = review_resume.main([str(source), *options])
        return code, out.getvalue(), err.getvalue()

    def output_path(self, out, label):
        paths = [line.removeprefix(label) for line in out.splitlines() if line.startswith(label)]
        self.assertEqual(len(paths), 1, out)
        return Path(paths[0])

    def fixture(self, body, preamble=""):
        source = self.root / "chosen.tex"
        source.write_text(
            "\\documentclass{resume}\n" + preamble
            + "\n\\begin{document}\n" + body + "\n\\end{document}\n",
            encoding="utf-8",
        )
        return source

    def assert_private_output(self, pdf):
        self.assertEqual(pdf.parent.parent, self.root / ".context" / "final-review")
        self.assertTrue(pdf.is_file())
        self.assertTrue((pdf.parent / "latexmk-output.txt").is_file())

    def test_starter_zip_in_spaced_folder_builds_only_chosen_entry(self):
        project = self.root / "starter project"
        project.mkdir()
        files = check_starter_builds.read_archive(ROOT / "downloads/new-grad-resume.zip")
        for name, content in files.items():
            (project / name).write_bytes(content)
        (project / "unselected.tex").write_text(r"\undefinedcommand", encoding="utf-8")
        code, out, err = self.run_review(project / "resume.tex", "--max-pages", "1")
        self.assertEqual(code, 3, out + err)
        self.assertEqual(err, "")
        self.assertIn("PLACEHOLDERS:", out)
        self.assertIn("Command page limit: 1 of 1 allowed.", out)
        self.assertIn(str((project / "resume.tex").resolve()), out)
        pdf = self.output_path(out, "Built PDF: ")
        self.assert_private_output(pdf)
        check_pdf_text.check_pdf(pdf, "new-grad")
        self.assertEqual(list(self.root.rglob("*.pdf")), [pdf])
        self.assertEqual(set(path.name for path in project.iterdir()), set(files) | {"unselected.tex"})

    def test_named_version_uses_shared_files_without_building_base(self):
        for relative in package_application_versions.SOURCES.values():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        project = self.root / "examples/application-versions"
        (project / "resume.tex").write_text(r"\undefinedcommand", encoding="utf-8")
        code, out, err = self.run_review(project / "backend.tex")
        self.assertEqual(code, 3, out + err)
        pdf = self.output_path(out, "Built PDF: ")
        self.assertEqual(pdf.name, "backend.pdf")
        self.assert_private_output(pdf)
        check_application_versions.check_selection(
            check_resume.extract_text(pdf), check_application_versions.SELECTIONS["backend"],
        )
        self.assertEqual(list(self.root.rglob("*.pdf")), [pdf])
        self.assertFalse((project / "backend.log").exists())

    def test_failed_rebuild_does_not_accept_previous_or_source_pdf(self):
        source = self.fixture("Completed resume content.")
        code, out, err = self.run_review(source)
        self.assertEqual(code, 0, out + err)
        previous_pdf = self.output_path(out, "Built PDF: ")
        previous_bytes = previous_pdf.read_bytes()
        stale_pdf = source.with_suffix(".pdf")
        stale_pdf.write_bytes(previous_bytes)
        source.write_text(r"\documentclass{resume}\begin{document}\undefinedcommand\end{document}", encoding="utf-8")
        code, out, err = self.run_review(source)
        self.assertEqual(code, 1, out + err)
        self.assertIn("Compilation failed", err)
        self.assertNotIn("Built PDF:", out)
        self.assertNotIn("Text checks:", out)
        self.assertNotIn(str(previous_pdf), out + err)
        self.assertEqual(previous_pdf.read_bytes(), previous_bytes)
        self.assertEqual(stale_pdf.read_bytes(), previous_bytes)
        failed_log = self.output_path(out, "Build log: ")
        self.assertNotEqual(failed_log.parent, previous_pdf.parent)
        self.assertIn("Undefined control sequence", failed_log.read_text(encoding="utf-8"))

    def test_source_and_command_page_limits_report_separately(self):
        source = self.fixture(
            r"First page.\newpage Second page.",
            r"\resumepagelimit{1}\resumepagelimit{wrong}",
        )
        code, out, err = self.run_review(source)
        self.assertEqual(code, 3, out + err)
        self.assertIn("Invalid page limit.", out)
        self.assertIn("Page limit exceeded: 2 pages; limit 1.", out)
        self.assertIn("Use a whole number", out)
        self.assertIn("Cut less relevant content", out)
        self.assertIn("Text checks: 2 page(s)", out)
        code, out, err = self.run_review(source, "--max-pages", "1")
        self.assertEqual(code, 1, out + err)
        self.assertIn("Page limit: found 2 pages; --max-pages is 1", err)
        self.assertIn("application's instructions", err)

    def test_no_page_budget_allows_multiple_pages_without_claiming_a_limit(self):
        source = self.fixture(r"First page.\newpage Second page.").rename(self.root / "build.tex")
        code, out, err = self.run_review(source)
        self.assertEqual(code, 0, out + err)
        build_log = self.output_path(out, "Build log: ")
        latex_log = self.output_path(out, "LaTeX log (if created): ")
        self.assertNotEqual(build_log, latex_log)
        self.assertEqual(latex_log.name, "build.log")
        self.assertIn("This is XeTeX", latex_log.read_text(encoding="utf-8"))
        self.assertIn("Text checks: 2 page(s)", out)
        self.assertIn("Command page limit: not checked", out)
        self.assertIn("does not establish that a source limit is enabled", out)
        self.assertIn("manual review is still needed", out)

    def test_project_output_settings_cannot_redirect_review_files(self):
        source = self.fixture("Completed resume content.")
        protected = [self.root / name for name in ("output/pdf", "preview", "downloads")]
        for directory in protected:
            directory.mkdir(parents=True)
            (directory / "existing.pdf").write_bytes(b"existing published bytes")
        (self.root / "latexmkrc").write_text(
            "$pdf_mode = 5;\n$aux_dir = 'output/pdf';\n"
            "$out_dir = 'preview';\n$out2_dir = 'downloads';\n",
            encoding="utf-8",
        )
        code, out, err = self.run_review(source)
        self.assertEqual(code, 0, out + err)
        self.assert_private_output(self.output_path(out, "Built PDF: "))
        for directory in protected:
            self.assertEqual(list(directory.iterdir()), [directory / "existing.pdf"])
            self.assertEqual((directory / "existing.pdf").read_bytes(), b"existing published bytes")

    def test_blank_page_fails_extraction_after_successful_compile(self):
        source = self.fixture(r"First page.\newpage\null")
        code, out, err = self.run_review(source)
        self.assertEqual(code, 1, out + err)
        self.assertIn("Built PDF:", out)
        self.assertIn("PDF extraction check: Page 2 has no extractable text.", err)
        self.assertNotIn("Text checks:", out)
        self.assertNotIn("Automated checks completed", out)

    def test_real_script_entrypoint_preserves_all_published_artifacts(self):
        before = published_files()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/review_resume.py"),
             str(ROOT / "templates/new-grad-resume.tex"), "--max-pages", "1"],
            cwd=self.root, capture_output=True, encoding="utf-8", timeout=240,
        )
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        pdf = self.output_path(result.stdout, "Built PDF: ")
        self.assertEqual(pdf.parent.parent, ROOT / ".context/final-review")
        self.addCleanup(shutil.rmtree, pdf.parent)
        self.assertEqual(pdf.name, "new-grad-resume.pdf")
        self.assertEqual(list(pdf.parent.glob("*.pdf")), [pdf])
        check_pdf_text.check_pdf(pdf, "new-grad")
        self.assertEqual(published_files(), before)


def main():
    missing = [name for name in ("latexmk", "xelatex", "pdftotext") if shutil.which(name) is None]
    if missing:
        print("FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX, latexmk, and Poppler.", file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinalReviewBuildTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
