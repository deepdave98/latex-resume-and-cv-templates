"""Personal PDF checker tests; no TeX or Poppler required."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_resume as checker


class TextChecks(unittest.TestCase):
    def test_edited_content_needs_no_snapshot(self):
        self.assertEqual(checker.check_text("My own project and education.\f"), 1)

    def test_optional_limit_is_not_an_implicit_one_page_rule(self):
        self.assertEqual(checker.check_text("Experience\fProjects\fSkills\f"), 3)

    def test_limit_accepts_equal_or_fewer_pages(self):
        self.assertEqual(checker.check_text("Experience\fSkills\f", max_pages=2), 2)
        self.assertEqual(checker.check_text("Projects\f", max_pages=2), 1)

    def test_limit_rejects_extra_pages(self):
        with self.assertRaisesRegex(checker.CheckError, "Found 2 pages; the chosen limit is 1"):
            checker.check_text("Experience\fSkills\f", max_pages=1)

    def test_empty_extraction_fails(self):
        for text in ("", " \n\t"):
            with self.subTest(text=repr(text)), self.assertRaisesRegex(checker.CheckError, "No extractable text"):
                checker.check_text(text)

    def test_empty_pages_are_preserved_and_fail(self):
        for text, number in (("\f", 1), ("\fSkills\f", 1), ("Skills\f\f", 2), ("A\f \n\fB\f", 2)):
            with self.subTest(text=repr(text)), self.assertRaisesRegex(checker.CheckError, f"Page {number} has no extractable text"):
                checker.check_text(text)

    def test_trailing_whitespace_is_not_an_extra_page(self):
        self.assertEqual(checker.check_text("Projects\f \n"), 1)

    def test_output_without_final_separator_still_works(self):
        self.assertEqual(checker.check_text("Projects\fSkills"), 2)

    def test_line_whitespace_ligatures_and_punctuation_are_valid(self):
        text = "\r\nProﬁled\tAPI. • C++ / C#; 25% – €10 — naïve\nhello@example.com\f"
        self.assertEqual(checker.check_text(text), 1)

    def test_international_text_and_joining_characters_are_valid(self):
        self.assertEqual(checker.check_text("José 中文 العربية می\u200cروم 👩\u200d💻\f"), 1)

    def test_format_characters_alone_are_not_page_content(self):
        with self.assertRaisesRegex(checker.CheckError, "Page 1 has no extractable text"):
            checker.check_text("\u200b\u200d\f")

    def test_replacement_private_use_and_controls_fail(self):
        for char in ("\ufffd", "\ue000", "\x00", "\x1b", "\x7f", "\x85", "\ud800", "\u0378"):
            with self.subTest(char=repr(char)), self.assertRaisesRegex(checker.CheckError, f"U\\+{ord(char):04X}"):
                checker.check_text(f"Private applicant {char}name\f")

    def test_character_error_names_page_without_quoting_content(self):
        with self.assertRaises(checker.CheckError) as caught:
            checker.check_text("Projects\fPRIVATE_SENTINEL\x00\f")
        self.assertIn("Page 2", str(caught.exception))
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_does_not_claim_to_detect_missing_or_reordered_words(self):
        self.assertEqual(checker.check_text("Skills Education API\f"), 1)


class ExtractionChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="personal resume tests ")
        self.addCleanup(self.temporary.cleanup)
        self.pdf = Path(self.temporary.name) / "-my resume.pdf"
        self.pdf.write_bytes(b"%PDF-placeholder")
        self.tool = patch.object(checker.shutil, "which", return_value="pdftotext")
        self.tool.start()
        self.addCleanup(self.tool.stop)

    def test_missing_input_fails_before_running_poppler(self):
        with patch.object(checker.subprocess, "run") as run:
            with self.assertRaisesRegex(checker.CheckError, "PDF not found"):
                checker.extract_text(self.pdf.parent / "missing.pdf")
        run.assert_not_called()

    def test_directory_is_not_a_pdf(self):
        with self.assertRaisesRegex(checker.CheckError, "not a file"):
            checker.extract_text(self.pdf.parent)

    def test_empty_file_is_not_a_pdf(self):
        self.pdf.write_bytes(b"")
        with self.assertRaisesRegex(checker.CheckError, "input file is empty"):
            checker.extract_text(self.pdf)

    def test_read_permission_error_does_not_echo_path(self):
        with patch.object(Path, "open", side_effect=PermissionError("PRIVATE_SENTINEL")):
            with self.assertRaises(checker.CheckError) as caught:
                checker.extract_text(self.pdf)
        self.assertIn("permissions", str(caught.exception))
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_invalid_path_is_a_controlled_error(self):
        with self.assertRaisesRegex(checker.CheckError, "path and permissions"):
            checker.extract_text(Path("bad\x00path.pdf"))

    def test_missing_poppler_is_actionable(self):
        with patch.object(checker.shutil, "which", return_value=None):
            with self.assertRaisesRegex(checker.CheckError, "Install Poppler"):
                checker.extract_text(self.pdf)

    def test_spaces_and_leading_dash_are_not_shell_or_poppler_options(self):
        result = subprocess.CompletedProcess([], 0, stdout="Projects\f", stderr="")
        with patch.object(checker.subprocess, "run", return_value=result) as run:
            self.assertEqual(checker.extract_text(self.pdf), "Projects\f")
        self.assertEqual(
            run.call_args.args[0],
            ["pdftotext", "-layout", "-enc", "UTF-8", str(self.pdf.resolve()), "-"],
        )
        self.assertFalse(run.call_args.kwargs.get("shell", False))
        self.assertEqual(run.call_args.kwargs["timeout"], 30)
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_corrupt_and_locked_pdf_errors_do_not_echo_stderr(self):
        for code in (1, 2, 3, 99):
            error = subprocess.CalledProcessError(code, [], output="PRIVATE_SENTINEL", stderr="PRIVATE_SENTINEL")
            with self.subTest(code=code), patch.object(checker.subprocess, "run", side_effect=error):
                with self.assertRaises(checker.CheckError) as caught:
                    checker.extract_text(self.pdf)
            self.assertIn("could not read", str(caught.exception))
            self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_timeout_does_not_echo_partial_text(self):
        error = subprocess.TimeoutExpired([], 30, output="PRIVATE_SENTINEL", stderr="PRIVATE_SENTINEL")
        with patch.object(checker.subprocess, "run", side_effect=error):
            with self.assertRaises(checker.CheckError) as caught:
                checker.extract_text(self.pdf)
        self.assertIn("timed out after 30 seconds", str(caught.exception))
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_poppler_warning_is_not_silently_accepted_or_printed(self):
        result = subprocess.CompletedProcess([], 0, stdout="Projects\f", stderr="PRIVATE_SENTINEL")
        with patch.object(checker.subprocess, "run", return_value=result):
            with self.assertRaises(checker.CheckError) as caught:
                checker.extract_text(self.pdf)
        self.assertIn("reported a warning", str(caught.exception))
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_invalid_utf8_is_a_controlled_error(self):
        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")
        with patch.object(checker.subprocess, "run", side_effect=error):
            with self.assertRaisesRegex(checker.CheckError, "invalid UTF-8"):
                checker.extract_text(self.pdf)

    def test_unusable_poppler_is_a_controlled_error(self):
        with patch.object(checker.subprocess, "run", side_effect=OSError("PRIVATE_SENTINEL")):
            with self.assertRaises(checker.CheckError) as caught:
                checker.extract_text(self.pdf)
        self.assertIn("Poppler installation", str(caught.exception))
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_check_pdf_connects_extraction_and_page_limit(self):
        with patch.object(checker, "extract_text", return_value="A\fB\f") as extract:
            with self.assertRaisesRegex(checker.CheckError, "chosen limit is 1"):
                checker.check_pdf(self.pdf, max_pages=1)
        extract.assert_called_once_with(self.pdf, max_bytes=None)


class CommandChecks(unittest.TestCase):
    def run_cli(self, args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_success_reports_scope_not_private_contents(self):
        with patch.object(checker, "extract_text", return_value="PRIVATE_SENTINEL\f"):
            code, out, err = self.run_cli(["private applicant.pdf"])
        self.assertEqual(code, 0)
        self.assertIn("PASS: 1 page;", out)
        self.assertIn("Extraction only", out)
        self.assertNotIn("PRIVATE_SENTINEL", out + err)
        self.assertNotIn("private applicant", out + err)
        self.assertEqual(err, "")

    def test_failure_returns_nonzero_without_private_contents(self):
        with patch.object(checker, "extract_text", return_value="PRIVATE_SENTINEL\x00\f"):
            code, out, err = self.run_cli(["private applicant.pdf"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("FAIL:", err)
        self.assertNotIn("PRIVATE_SENTINEL", out + err)

    def test_options_after_path_and_dash_separator(self):
        with patch.object(checker, "check_pdf", return_value=2) as check:
            code, out, err = self.run_cli(["folder/my resume.pdf", "--max-pages", "2"])
            check.assert_called_once_with(Path("folder/my resume.pdf"), max_pages=2, max_bytes=None)
        self.assertEqual(code, 0)
        self.assertIn("2 pages;", out)
        with patch.object(checker, "check_pdf", return_value=1) as check:
            self.run_cli(["--max-pages", "1", "--", "-resume.pdf"])
            check.assert_called_once_with(Path("-resume.pdf"), max_pages=1, max_bytes=None)

    def test_page_limit_requires_positive_integer(self):
        for value in ("0", "-1", "1.5", "many"):
            with self.subTest(value=value), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    checker.main(["resume.pdf", "--max-pages", value])
            self.assertEqual(caught.exception.code, 2)

    def test_help_states_limits_and_does_not_require_poppler(self):
        out = StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            checker.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        for text in ("no uploads", "reading order", "ATS compatibility", "no limit by default"):
            self.assertIn(text, out.getvalue())

    def test_script_runs_without_repository_files(self):
        with tempfile.TemporaryDirectory(prefix="standalone checker ") as temporary:
            copied = Path(temporary) / "check_resume.py"
            copied.write_bytes(Path(checker.__file__).read_bytes())
            result = subprocess.run(
                [sys.executable, str(copied), "--help"], cwd=temporary,
                capture_output=True, encoding="utf-8", timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no uploads", result.stdout)


if __name__ == "__main__":
    unittest.main()
