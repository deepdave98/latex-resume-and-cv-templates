"""Final-review failure handling; no TeX or Poppler required."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import os
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
        extract.assert_called_once_with(pdf, max_bytes=None)
        self.assertTrue(pdf.is_relative_to(self.root / ".context/final-review"))
        self.assertIn("Command page limit: not checked", out)
        self.assertIn("does not establish", out)
        self.assertIn("manual review is still needed", out)
        self.assertNotIn("Exported PDF:", out)

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
        self.assertIn("PDF check", err)
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
                self.assertIn("PDF check", err)
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

    def test_upload_size_checks_the_new_pdf_before_poppler(self):
        self.assertEqual(len(self.pdf_content), 8)
        for limit, expected in (("0.000008", 0), ("0.000007", 1)):
            destination = self.root / f"size-{limit}.pdf"
            out, err = StringIO(), StringIO()
            result = subprocess.CompletedProcess([], 0, stdout="Resume\f", stderr="")
            with (
                self.subTest(limit=limit),
                patch.object(review, "run_build", side_effect=self.compile),
                patch.object(review.check_resume.subprocess, "run", return_value=result) as poppler,
                redirect_stdout(out), redirect_stderr(err),
            ):
                code = review.main([
                    str(self.source), "--max-size-mb", limit, "--max-pages", "1",
                    "--export-pdf", str(destination),
                ])
            self.assertEqual(code, expected, out.getvalue() + err.getvalue())
            self.assertEqual(destination.exists(), expected == 0)
            pdf = self.output_dirs[-1] / f"{self.source.stem}.pdf"
            self.assertEqual(pdf.read_bytes(), self.pdf_content)
            if expected == 0:
                poppler.assert_called_once()
                self.assertIn("8-byte limit", out.getvalue())
            else:
                poppler.assert_not_called()
                self.assertIn("8 bytes, above the 7-byte limit", err.getvalue())
                self.assertNotIn("Text checks:", out.getvalue())

    def test_source_required_and_arguments_reject_multiple_sources_or_bad_limits(self):
        for args in (
            [], [str(self.source), str(self.source)],
            [str(self.project)], [str(self.root / "missing.tex")],
            [str(self.source), "--max-pages", "0"],
            [str(self.source), "--max-pages", "1.5"],
            [str(self.source), "--max-size-mb", "NaN"],
            [str(self.source), "--max-size-mb", "0"],
        ):
            with self.subTest(args=args), redirect_stderr(StringIO()), patch.object(review, "run_build") as build:
                with self.assertRaises(SystemExit) as caught:
                    review.main(args)
                self.assertEqual(caught.exception.code, 2)
                build.assert_not_called()

    def test_export_copies_only_the_fresh_checked_pdf(self):
        destination = self.project / "Applicant Resume.PDF"
        self.source.with_suffix(".pdf").write_bytes(b"stale source-adjacent PDF")
        code, out, err, _, extract = self.run_review(("--export-pdf", str(destination)))
        self.assertEqual(code, 0, err)
        checked = extract.call_args.args[0]
        self.assertEqual(destination.read_bytes(), checked.read_bytes())
        self.assertEqual(destination.read_bytes(), self.pdf_content)
        self.assertNotEqual(destination.stat().st_ino, checked.stat().st_ino)
        self.assertIn(f"Exported PDF: {destination}", out)
        self.assertIn("manual review is still needed", out)
        self.assertFalse(list(destination.parent.glob(".resume-export-*")))

    def test_export_expands_home_and_relative_paths(self):
        # Validate home expansion without changing the environment or writing there.
        filename = f"resume-export-{self.root.name}.pdf"
        self.assertEqual(
            review.export_destination(Path("~") / filename), Path.home().resolve() / filename,
        )
        relative = os.path.relpath(self.root / "Relative Resume.pdf")
        code, _, err, _, _ = self.run_review(("--export-pdf", relative))
        self.assertEqual(code, 0, err)
        self.assertEqual((self.root / "Relative Resume.pdf").read_bytes(), self.pdf_content)

    def test_export_rejects_invalid_or_existing_paths_before_building(self):
        existing = self.root / "existing.pdf"
        existing.write_bytes(b"keep this file")
        directory = self.root / "directory.pdf"
        directory.mkdir()
        symlink = self.root / "link.pdf"
        symlink.symlink_to(existing)
        dangling = self.root / "dangling.pdf"
        dangling.symlink_to(self.root / "absent.pdf")
        for destination in (
            self.root / "resume.txt", self.root / "missing" / "resume.pdf",
            existing, directory, symlink, dangling, existing / "resume.pdf",
        ):
            with self.subTest(destination=destination), patch.object(review, "run_build") as build:
                with redirect_stderr(StringIO()) as err, self.assertRaises(SystemExit) as caught:
                    review.main([str(self.source), "--export-pdf", str(destination)])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("Cannot use --export-pdf", err.getvalue())
                build.assert_not_called()
        self.assertEqual(existing.read_bytes(), b"keep this file")
        self.assertTrue(symlink.is_symlink())
        self.assertTrue(dangling.is_symlink())
        self.assertFalse((self.root / "missing").exists())
        self.assertFalse((self.root / ".context").exists())

    def test_failed_or_incomplete_review_never_starts_export(self):
        destination = self.root / "Resume.pdf"
        cases = (
            {"returncode": 1},
            {"write_pdf": False},
            {"write_log": False},
            {"text": "\f"},
            {"error": review.check_resume.CheckError("File size exceeds the limit.")},
            {"extra": ("--max-pages", "1"), "text": "First\fSecond\f"},
            {"log": review.PLACEHOLDER + "name."},
            {"log": review.PAGE_EXCEEDED + " 2 pages; limit 1."},
            {"log": review.CONTACT_UNSUPPORTED + "phone format; contact is not linked."},
            {"log": r"Overfull \hbox (40pt too wide)"},
        )
        for case in cases:
            self.returncode, self.write_pdf, self.write_log, self.log = 0, True, True, "This is XeTeX.\n"
            options = ("--export-pdf", str(destination), *case.get("extra", ()))
            for name in ("returncode", "write_pdf", "write_log", "log"):
                if name in case:
                    setattr(self, name, case[name])
            with self.subTest(case=case), patch.object(review, "export_pdf") as export:
                code, out, _, _, _ = self.run_review(
                    options, text=case.get("text", "Resume\f"), error=case.get("error"),
                )
                self.assertEqual(code, 3 if "log" in case else 1)
                export.assert_not_called()
                self.assertFalse(destination.exists())
                self.assertNotIn("Exported PDF:", out)

    def test_export_does_not_reuse_a_previous_successful_output(self):
        first = self.root / "first.pdf"
        second = self.root / "second.pdf"
        code, _, err, _, _ = self.run_review(("--export-pdf", str(first)))
        self.assertEqual(code, 0, err)
        original = first.read_bytes()
        self.returncode = 1
        self.pdf_content = b"partial new PDF"
        code, out, _, _, _ = self.run_review(("--export-pdf", str(second)))
        self.assertEqual(code, 1)
        self.assertFalse(second.exists())
        self.assertEqual(first.read_bytes(), original)
        self.assertNotIn("Exported PDF:", out)

    def test_copy_failure_removes_partial_staging_file(self):
        destination = self.root / "Resume.pdf"

        def fail_copy(source, output):
            output.write(b"partial PDF")
            raise OSError("disk full")

        with patch.object(review.shutil, "copyfileobj", side_effect=fail_copy), patch.object(review.os, "link") as link:
            code, out, err, _, _ = self.run_review(("--export-pdf", str(destination)))
        self.assertEqual(code, 1)
        self.assertIn("Cannot export PDF", err)
        self.assertNotIn("Exported PDF:", out)
        link.assert_not_called()
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob(".resume-export-*")))

    def test_export_link_failure_leaves_no_destination_or_staging_file(self):
        destination = self.root / "Resume.pdf"
        with patch.object(review.os, "link", side_effect=OSError("hard links unavailable")):
            code, out, err, _, _ = self.run_review(("--export-pdf", str(destination)))
        self.assertEqual(code, 1)
        self.assertIn("supports hard links", err)
        self.assertNotIn("Exported PDF:", out)
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob(".resume-export-*")))

    def test_late_export_collision_never_replaces_a_file_or_symlink(self):
        target = self.root / "other.pdf"
        target.write_bytes(b"keep target")
        native_link = os.link
        for symlink in (False, True):
            destination = self.root / f"collision-{symlink}.pdf"

            def collide(source, output):
                self.assertEqual(Path(source).read_bytes(), self.pdf_content)
                if symlink:
                    output.symlink_to(target)
                else:
                    output.write_bytes(b"keep collision")
                native_link(source, output)

            with self.subTest(symlink=symlink), patch.object(review.os, "link", side_effect=collide):
                code, out, err, _, _ = self.run_review(("--export-pdf", str(destination)))
            self.assertEqual(code, 1)
            self.assertIn("Cannot export PDF", err)
            self.assertNotIn("Exported PDF:", out)
            self.assertEqual(destination.is_symlink(), symlink)
            self.assertEqual(destination.read_bytes(), b"keep target" if symlink else b"keep collision")
            self.assertFalse(list(self.root.glob(".resume-export-*")))
        self.assertEqual(target.read_bytes(), b"keep target")

    def test_pdf_changed_during_checks_is_not_exported(self):
        destination = self.root / "Resume.pdf"

        def change_pdf(pdf, **kwargs):
            pdf.write_bytes(b"different PDF bytes")
            return "Resume\f"

        code, out, err, _, _ = self.run_review(("--export-pdf", str(destination)), error=change_pdf)
        self.assertEqual(code, 1)
        self.assertIn("changed after its checks", err)
        self.assertNotIn("Exported PDF:", out)
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob(".resume-export-*")))

    def test_pdf_changed_while_copying_is_not_exported(self):
        destination = self.root / "Resume.pdf"
        native_copy = review.shutil.copyfileobj

        def change_pdf(source, output):
            native_copy(source, output)
            Path(source.name).write_bytes(b"changed during copy")

        with patch.object(review.shutil, "copyfileobj", side_effect=change_pdf):
            code, _, err, _, _ = self.run_review(("--export-pdf", str(destination)))
        self.assertEqual(code, 1)
        self.assertIn("changed while copying", err)
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob(".resume-export-*")))

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
