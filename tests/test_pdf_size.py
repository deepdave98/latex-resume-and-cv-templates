"""Exact upload-size checks without TeX or Poppler."""

import argparse
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


class SizeLimitTests(unittest.TestCase):
    def test_decimal_units_and_fractional_bytes(self):
        for value, expected in (("1", 1_000_000), ("0.5", 500_000), (".25", 250_000),
                                ("0.000001", 1), ("0.0000019", 1), ("1.0000009", 1_000_000),
                                ("1.000000999999999999999999999999", 1_000_000)):
            with self.subTest(value=value):
                self.assertEqual(checker.megabyte_limit(value), expected)

    def test_invalid_limits_are_argument_errors(self):
        for value in ("", "0", "-1", "nan", "NaN", "Infinity", "1e6", "1,5", "2MB", "1_000", ".", " 1", "0.0000009", "9" * 33):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                checker.megabyte_limit(value)

    def test_exact_size_passes_and_one_byte_over_fails_before_poppler(self):
        with tempfile.TemporaryDirectory() as temporary:
            pdf = Path(temporary) / "PRIVATE_SENTINEL.pdf"
            pdf.write_bytes(b"%PDF-" + b"x" * 95)
            before = pdf.read_bytes(), pdf.stat().st_mtime_ns
            result = subprocess.CompletedProcess([], 0, stdout="Resume\f", stderr="")
            with patch.object(checker.shutil, "which", return_value="pdftotext"), \
                    patch.object(checker.subprocess, "run", return_value=result) as run:
                self.assertEqual(checker.check_pdf(pdf, max_pages=1, max_bytes=100), 1)
                run.assert_called_once()
            with patch.object(checker.shutil, "which") as which, \
                    patch.object(checker.subprocess, "run") as run:
                with self.assertRaisesRegex(checker.CheckError, "100 bytes; limit 99 bytes") as caught:
                    checker.check_pdf(pdf, max_bytes=99)
                self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))
                which.assert_not_called()
                run.assert_not_called()
            self.assertEqual((pdf.read_bytes(), pdf.stat().st_mtime_ns), before)

    def test_size_check_does_not_skip_text_or_page_checks(self):
        with patch.object(checker, "extract_text", return_value="A\fB\f"):
            with self.assertRaisesRegex(checker.CheckError, "chosen limit is 1"):
                checker.check_pdf(Path("resume.pdf"), max_pages=1, max_bytes=500_000)
        with patch.object(checker, "extract_text", return_value="\f"):
            with self.assertRaisesRegex(checker.CheckError, "no extractable text"):
                checker.check_pdf(Path("resume.pdf"), max_bytes=500_000)

    def test_cli_combines_limits_and_reports_size_scope(self):
        out = StringIO()
        with patch.object(checker, "check_pdf", return_value=1) as check, redirect_stdout(out):
            self.assertEqual(checker.main(["--max-size-mb", "0.5", "--max-pages", "1", "--", "-resume.pdf"]), 0)
        check.assert_called_once_with(Path("-resume.pdf"), max_pages=1, max_bytes=500_000)
        self.assertIn("500,000-byte limit", out.getvalue())

    def test_invalid_cli_size_returns_two_without_reading_pdf(self):
        with patch.object(checker, "check_pdf") as check, redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as caught:
                checker.main(["resume.pdf", "--max-size-mb", "NaN"])
        self.assertEqual(caught.exception.code, 2)
        check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
