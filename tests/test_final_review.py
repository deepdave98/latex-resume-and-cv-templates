"""Final-review failure handling; no TeX or Poppler required."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_resume as review


class FinalReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="final review ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "my starter"
        self.project.mkdir()
        self.source = self.project / "-my resume.tex"
        self.source.write_text("Resume source", encoding="utf-8")
        root = patch.object(review, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)
        tools = patch.object(review.shutil, "which", side_effect=lambda name: f"/tools/{name}")
        tools.start()
        self.addCleanup(tools.stop)
        self.log = "This is XeTeX.\n"
        self.pdf_content = b"%PDF-new"
        self.returncode = 0
        self.write_log = True
        self.write_pdf = True
        self.output_dirs = []

    def compile(self, args, **kwargs):
        build_dir = Path(next(arg.split("=", 1)[1] for arg in args if arg.startswith("-outdir=")))
        self.assertFalse((build_dir / f"{self.source.stem}.pdf").exists())
        self.output_dirs.append(build_dir)
        if self.write_pdf:
            (build_dir / f"{self.source.stem}.pdf").write_bytes(self.pdf_content)
        if self.write_log:
            (build_dir / f"{self.source.stem}.log").write_text(self.log, encoding="utf-8")
        return self.returncode

    def run_review(self, extra=(), text="Applicant's own work.\f", error=None):
        out, err = StringIO(), StringIO()
        with (
            patch.object(review, "run_build", side_effect=self.compile) as build,
            patch.object(review.check_resume, "extract_text", return_value=text, side_effect=error) as extract,
            redirect_stdout(out), redirect_stderr(err),
        ):
            code = review.main([str(self.source), *extra])
        return code, out.getvalue(), err.getvalue(), build, extract

    def test_single_source_and_all_output_paths_are_explicit(self):
        code, out, err, build, extract = self.run_review()
        self.assertEqual(code, 0, err)
        args = build.call_args.args[0]
        self.assertEqual([arg for arg in args if arg.endswith(".tex")], [str(self.source)])
        self.assertEqual(build.call_args.kwargs["cwd"], self.project)
        self.assertEqual(build.call_args.kwargs["timeout"], review.BUILD_TIMEOUT)
        self.assertFalse(build.call_args.kwargs.get("shell", False))
        self.assertIn(f"-auxdir={self.output_dirs[0]}", args)
        self.assertIn("$out2_dir = '';", args)
        for label in ("Source:", "Build log:", "LaTeX log (if created):", "Built PDF:"):
            self.assertIn(label, out)
        pdf = self.output_dirs[0] / f"{self.source.stem}.pdf"
        extract.assert_called_once_with(pdf)
        self.assertTrue(pdf.is_relative_to(self.root / ".context/final-review"))
        self.assertIn("Command page limit: not checked", out)
        self.assertIn("does not establish", out)
        self.assertIn("manual review is still needed", out)

    def test_repository_template_reuses_root_working_directory(self):
        (self.root / "templates").mkdir()
        self.source = self.root / "templates/resume.tex"
        self.source.write_text("Resume source", encoding="utf-8")
        code, _, _, build, _ = self.run_review()
        self.assertEqual(code, 0)
        self.assertEqual(build.call_args.kwargs["cwd"], self.root)

    def test_failed_rebuild_does_not_check_or_report_old_pdf_or_partial_pdf(self):
        code, out, _, _, _ = self.run_review()
        self.assertEqual(code, 0)
        old_pdf = next(self.output_dirs[0].glob("*.pdf"))
        old_bytes = old_pdf.read_bytes()
        self.returncode = 1
        code, out, err, _, extract = self.run_review()
        self.assertEqual(code, 1)
        self.assertNotIn("Built PDF:", out)
        self.assertNotIn(str(old_pdf), out + err)
        self.assertIn("first error", err)
        extract.assert_not_called()
        self.assertNotEqual(self.output_dirs[0], self.output_dirs[1])
        self.assertEqual(old_pdf.read_bytes(), old_bytes)

    def test_zero_exit_without_pdf_or_with_empty_pdf_is_a_failure(self):
        for empty in (False, True):
            with self.subTest(empty=empty):
                self.write_pdf = empty
                self.pdf_content = b""
                code, out, err, _, extract = self.run_review()
                self.assertEqual(code, 1)
                self.assertIn("expected PDF", err)
                self.assertNotIn("Built PDF:", out)
                extract.assert_not_called()

    def test_missing_log_does_not_claim_no_reminders(self):
        self.write_log = False
        code, out, err, _, extract = self.run_review()
        self.assertEqual(code, 1)
        self.assertIn("warning checks are incomplete", err)
        self.assertNotIn("no class reminders", out)
        extract.assert_not_called()

    def test_empty_log_cannot_pass_warning_checks(self):
        self.log = ""
        code, out, err, _, extract = self.run_review()
        self.assertEqual(code, 1)
        self.assertIn("LaTeX log is empty", err)
        self.assertIn("warning checks are incomplete", err)
        self.assertNotIn("no class reminders", out)
        extract.assert_not_called()

    def test_missing_tools_have_specific_remedies_and_no_build(self):
        for tool, remedy in (("latexmk", "TeX distribution"), ("xelatex", "XeLaTeX"), ("pdftotext", "Poppler")):
            with self.subTest(tool=tool), patch.object(
                review.shutil, "which", side_effect=lambda name: None if name == tool else f"/tools/{name}"
            ):
                code, out, err, build, extract = self.run_review()
            self.assertEqual(code, 1)
            self.assertIn(f"{tool} not found", err)
            self.assertIn(remedy, err)
            self.assertNotIn("Built PDF", out)
            build.assert_not_called()
            extract.assert_not_called()

    def test_timeout_and_spawn_error_do_not_check_pdf(self):
        for error, remedy in (
            (subprocess.TimeoutExpired([], review.BUILD_TIMEOUT), "exceeded"),
            (OSError("Cannot start compiler"), "permissions"),
        ):
            with self.subTest(error=type(error)), patch.object(self, "compile", side_effect=error):
                code, out, err, _, extract = self.run_review()
            self.assertEqual(code, 1)
            self.assertIn(remedy, err)
            self.assertNotIn("Built PDF:", out)
            extract.assert_not_called()

    def test_class_reminders_stay_distinct_from_extraction_success(self):
        for log, label, remedy in (
            (review.PLACEHOLDER + "name.", "PLACEHOLDERS: 1", "Replace sample values"),
            (review.PAGE_EXCEEDED + " 2 pages; limit 1.", "PAGE WARNING", "Cut less relevant content"),
            (review.PAGE_INVALID, "PAGE WARNING", "whole number"),
        ):
            with self.subTest(log=log):
                self.log = "\n" + log + "\n"
                code, out, err, _, _ = self.run_review()
                self.assertEqual(code, 3, err)
                for expected in (label, remedy, "log line 2", "Text checks: 1", "REVIEW NEEDED"):
                    self.assertIn(expected, out)
                self.assertNotIn("checks completed without", out)

    def test_unsupported_contacts_need_review_without_printing_private_values(self):
        self.log = "\n".join((
            review.CONTACT_UNSUPPORTED + "phone format; contact is not linked.",
            "PRIVATE_CONTACT_SENTINEL",
            review.CONTACT_UNSUPPORTED + "email format; contact is not linked.",
        ))
        code, out, err, _, _ = self.run_review()
        self.assertEqual(code, 3, err)
        self.assertIn("CONTACT LINKS: 2 unsupported format(s)", out)
        self.assertIn("log line 1", out)
        self.assertIn("phone country code", out)
        self.assertIn(r"\resumelink", out)
        self.assertIn("REVIEW NEEDED", out)
        self.assertNotIn("PRIVATE_CONTACT_SENTINEL", out + err)

    def test_overfull_boxes_need_review_without_printing_resume_text(self):
        self.log = "\n".join((
            r"Overfull \hbox (40.0pt too wide) in paragraph at lines 3--4",
            "PRIVATE_RESUME_SENTINEL",
            r"Overfull \vbox (2.0pt too high) detected at line 8",
        ))
        code, out, err, _, _ = self.run_review()
        self.assertEqual(code, 3, err)
        self.assertIn("LAYOUT OVERFLOW: 2 box warning(s)", out)
        self.assertIn("log line 1", out)
        self.assertIn("clipped or overflowing text", out)
        self.assertNotIn("PRIVATE_RESUME_SENTINEL", out + err)

    def test_underfull_boxes_alone_do_not_fail_the_review(self):
        self.log = r"Underfull \hbox (badness 10000) in paragraph at lines 3--4"
        code, out, err, _, _ = self.run_review()
        self.assertEqual(code, 0, err)
        self.assertNotIn("LAYOUT OVERFLOW:", out)

    def test_multiple_placeholder_reminders_count_only_final_log(self):
        self.log = "\n".join((review.PLACEHOLDER + "name.", review.PLACEHOLDER + "selected bullet."))
        code, out, _, _, _ = self.run_review()
        self.assertEqual(code, 3)
        self.assertIn("PLACEHOLDERS: 2 reminder(s)", out)
        self.assertIn("content/*.tex", out)

    def test_page_limit_is_optional_and_does_not_hide_extraction_errors(self):
        code, out, _, _, _ = self.run_review(text="First.\fSecond.\f")
        self.assertEqual(code, 0)
        self.assertIn("2 page(s)", out)
        code, out, err, _, _ = self.run_review(("--max-pages", "1"), text="First.\fSecond.\f")
        self.assertEqual(code, 1)
        self.assertIn("Page limit: found 2 pages", err)
        self.assertIn("application's instructions", err)
        code, out, err, _, _ = self.run_review(("--max-pages", "1"), text="First.\fBad \ufffd\f")
        self.assertEqual(code, 1)
        self.assertIn("PDF extraction check", err)
        self.assertIn("U+FFFD", err)
        self.assertNotIn("Text checks:", out)

    def test_extraction_failures_and_bad_text_never_print_private_text_or_success(self):
        for text, error in (
            ("", None),
            ("Work.\f\f", None),
            ("PRIVATE_SENTINEL\x00\f", None),
            ("", review.check_resume.CheckError("pdftotext could not read this PDF.")),
            ("", review.check_resume.CheckError("pdftotext reported a warning.")),
        ):
            with self.subTest(text=repr(text), error=error):
                code, out, err, _, _ = self.run_review(text=text, error=error)
                self.assertEqual(code, 1)
                self.assertIn("PDF extraction check", err)
                self.assertIn("offline reviewer", err)
                self.assertNotIn("Text checks:", out)
                self.assertNotIn("PRIVATE_SENTINEL", out + err)

    def test_symlink_output_root_is_rejected_without_writing_there(self):
        (self.root / ".context").symlink_to(self.project, target_is_directory=True)
        code, _, err, build, _ = self.run_review()
        self.assertEqual(code, 1)
        self.assertIn("must not be a symlink", err)
        self.assertFalse((self.project / "final-review").exists())
        build.assert_not_called()

    def test_source_required_and_arguments_reject_multiple_sources_or_bad_limits(self):
        for args in (
            [], [str(self.source), str(self.source)],
            [str(self.project)], [str(self.root / "missing.tex")],
            [str(self.source), "--max-pages", "0"],
            [str(self.source), "--max-pages", "1.5"],
        ):
            with self.subTest(args=args), redirect_stderr(StringIO()), patch.object(review, "run_build") as build:
                with self.assertRaises(SystemExit) as caught:
                    review.main(args)
                self.assertEqual(caught.exception.code, 2)
                build.assert_not_called()

    def test_help_needs_no_installed_tools(self):
        out = StringIO()
        with redirect_stdout(out), patch.object(review.shutil, "which") as tool:
            with self.assertRaises(SystemExit) as caught:
                review.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        tool.assert_not_called()
        self.assertIn("exactly one LaTeX entry file", out.getvalue())
        self.assertIn("reading order", " ".join(out.getvalue().split()))


class BuildTimeoutTests(unittest.TestCase):
    def test_timeout_stops_the_compiler_child(self):
        with tempfile.TemporaryDirectory(prefix="review timeout ") as temporary:
            root = Path(temporary)
            started = root / "compiler-started"
            escaped = root / "compiler-survived"
            child = (
                "from pathlib import Path; import time; "
                f"Path({str(started)!r}).touch(); time.sleep(2); "
                f"Path({str(escaped)!r}).touch()"
            )
            parent = (
                "import subprocess, sys, time; "
                f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(30)"
            )
            with (root / "build.log").open("w") as output:
                with self.assertRaises(subprocess.TimeoutExpired):
                    review.run_build([sys.executable, "-c", parent], cwd=root, stdout=output, timeout=1)
            self.assertTrue(started.exists(), "The compiler fixture did not start before the timeout")
            time.sleep(2.1)
            self.assertFalse(escaped.exists(), "The compiler kept running after the build timed out")


if __name__ == "__main__":
    unittest.main()
