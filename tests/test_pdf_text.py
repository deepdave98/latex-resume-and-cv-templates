"""Fault tests for the checker; these do not need TeX or Poppler."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import call, patch

import check_pdf_text as checker


class TextChecks(unittest.TestCase):
    def test_page_count_registry_covers_all_starters(self):
        self.assertEqual(
            checker.PAGE_COUNTS,
            {"new-grad": 1, "no-internship": 1, "experienced": 2,
             "ai-engineer": 1, "ml-engineer": 1, "graduate-admissions": 1},
        )

    def test_identical_text_passes(self):
        checker.compare_pages("resume", "Education\nBuilt API.\f", ["Education\nBuilt API."])

    def test_whitespace_and_ligatures_pass(self):
        checker.compare_pages("resume", "Skills\r\n  Proﬁled\tAPI.\f", ["Skills Profiled API."])

    def test_missing_word_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "Built API.\f", ["Built tested API."])

    def test_reordered_sections_fail(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "Skills Education\f", ["Education Skills"])

    def test_reordered_bullets_fail(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "• Tested API. • Built API.\f", ["• Built API. • Tested API."])

    def test_missing_bullet_marker_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "Built API.\f", ["• Built API."])

    def test_missing_punctuation_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "helloexample.com\f", ["hello@example.com"])

    def test_extra_blank_page_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "expected 1 pages, got 2"):
            checker.compare_pages("resume", "Education\f\f", ["Education"])

    def test_missing_page_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "expected 2 pages, got 1"):
            checker.compare_pages("resume", "Experience\f", ["Experience", "Skills"])

    def test_blank_page_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "no extractable text"):
            checker.compare_pages("resume", " \f", ["Education"])

    def test_empty_output_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "expected 1 pages, got 0"):
            checker.compare_pages("resume", "", ["Education"])

    def test_blank_baseline_fails(self):
        with self.assertRaisesRegex(checker.CheckError, "empty text baseline"):
            checker.compare_pages("resume", "Education\f", [""])

    def test_unmapped_and_control_characters_fail(self):
        for char in ("\ufffd", "\ue000", "\x00", "\u200b"):
            with self.subTest(char=repr(char)), self.assertRaisesRegex(checker.CheckError, "character U\\+"):
                checker.compare_pages("resume", f"Built {char}API.\f", ["Built API."])

    def test_hyphens_are_not_removed(self):
        with self.assertRaisesRegex(checker.CheckError, "extracted text changed"):
            checker.compare_pages("resume", "requestpath\f", ["request-path"])

    def test_multiple_pages_pass(self):
        checker.compare_pages("resume", "Experience\fSkills\f", ["Experience", "Skills"])

    def test_no_internship_uses_its_one_page_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            expected = Path(temporary)
            (expected / "no-internship-1.txt").write_text("Projects", encoding="utf-8")
            with patch.object(checker, "EXPECTED_DIR", expected), patch.object(
                checker, "extract_text", return_value="Projects\f"
            ):
                checker.check_pdf(Path("no-internship.pdf"), "no-internship")


class CommandChecks(unittest.TestCase):
    def test_missing_pdf_has_actionable_error(self):
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(checker.CheckError, "Build the templates first"):
                checker.extract_text(Path("missing.pdf"))

    def test_missing_poppler_has_actionable_error(self):
        with patch.object(Path, "is_file", return_value=True), patch.object(checker.shutil, "which", return_value=None):
            with self.assertRaisesRegex(checker.CheckError, "Install Poppler"):
                checker.extract_text(Path("resume.pdf"))

    def test_subprocess_failure_is_reported(self):
        error = subprocess.CalledProcessError(1, "pdftotext", stderr="Invalid PDF")
        with patch.object(Path, "is_file", return_value=True), patch.object(checker.shutil, "which", return_value="pdftotext"):
            with patch.object(checker.subprocess, "run", side_effect=error):
                with self.assertRaisesRegex(checker.CheckError, "Invalid PDF"):
                    checker.extract_text(Path("resume.pdf"))

    def test_paths_with_spaces_are_passed_without_a_shell(self):
        pdf = Path("a folder/resume.pdf")
        result = subprocess.CompletedProcess([], 0, stdout="Education\f", stderr="")
        with patch.object(Path, "is_file", return_value=True), patch.object(checker.shutil, "which", return_value="pdftotext"):
            with patch.object(checker.subprocess, "run", return_value=result) as run:
                self.assertEqual(checker.extract_text(pdf), "Education\f")
                self.assertEqual(run.call_args.args[0][-2:], [str(pdf.resolve()), "-"])
                self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_cli_reports_all_files_and_returns_failure(self):
        with patch.object(
            checker,
            "check_pdf",
            side_effect=[checker.CheckError("changed"), None, None, None, None, None],
        ) as check:
            with redirect_stderr(StringIO()), redirect_stdout(StringIO()):
                self.assertEqual(checker.main([]), 1)
            self.assertEqual(check.call_count, 6)

    def test_cli_returns_success(self):
        with patch.object(checker, "check_pdf") as check, redirect_stdout(StringIO()):
            self.assertEqual(checker.main([]), 0)
        self.assertEqual(
            check.call_args_list,
            [
                call(Path("build/new-grad/new-grad-resume.pdf"), "new-grad"),
                call(Path("build/no-internship/no-internship-resume.pdf"), "no-internship"),
                call(Path("build/experienced/experienced-resume.pdf"), "experienced"),
                call(Path("build/ai-engineer/ai-engineer-resume.pdf"), "ai-engineer"),
                call(Path("build/ml-engineer/ml-engineer-resume.pdf"), "ml-engineer"),
                call(Path("build/graduate-admissions/graduate-admissions-resume.pdf"), "graduate-admissions"),
            ],
        )

    def test_cli_accepts_no_internship_pdf_override(self):
        with patch.object(checker, "check_pdf") as check, redirect_stdout(StringIO()):
            self.assertEqual(
                checker.main(["--no-internship", "custom folder/no-internship.pdf"]),
                0,
            )
        self.assertEqual(
            check.call_args_list[1],
            call(Path("custom folder/no-internship.pdf"), "no-internship"),
        )

    def test_cli_accepts_ai_and_ml_pdf_overrides(self):
        with patch.object(checker, "check_pdf") as check, redirect_stdout(StringIO()):
            self.assertEqual(checker.main([
                "--ai-engineer", "custom folder/ai.pdf",
                "--ml-engineer", "custom folder/ml.pdf",
            ]), 0)
        self.assertEqual(check.call_args_list[3:5], [
            call(Path("custom folder/ai.pdf"), "ai-engineer"),
            call(Path("custom folder/ml.pdf"), "ml-engineer"),
        ])

    def test_cli_accepts_graduate_admissions_pdf_override(self):
        with patch.object(checker, "check_pdf") as check, redirect_stdout(StringIO()):
            self.assertEqual(checker.main([
                "--graduate-admissions", "custom folder/admissions.pdf",
            ]), 0)
        self.assertEqual(check.call_args_list[-1],
                         call(Path("custom folder/admissions.pdf"), "graduate-admissions"))


if __name__ == "__main__":
    unittest.main()
