"""Fault tests for application-version checks; no TeX or Poppler required."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import check_application_versions as checker


def archive_bytes(entries):
    output = BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(output, "w") as archive:
        warnings.simplefilter("ignore", UserWarning)
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


class ApplicationArchiveTests(unittest.TestCase):
    def read(self, entries=None, payload=None):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "applications.zip"
            archive.write_bytes(payload if payload is not None else archive_bytes(entries))
            return checker.read_archive(archive)

    def entries(self):
        return [(name, name.encode()) for name in sorted(checker.ARCHIVE_FILES)]

    def test_archive_has_exact_files(self):
        self.assertEqual(self.read(self.entries()), dict(self.entries()))

    def test_missing_extra_and_traversal_entries_fail(self):
        entries = self.entries()
        for variant in (entries[:-1], entries + [("private.txt", b"secret")], entries + [("../resume.cls", b"bad")], entries + [("/resume.cls", b"bad")]):
            with self.subTest(entries=variant), self.assertRaisesRegex(checker.ApplicationError, "unexpected ZIP contents"):
                self.read(variant)

    def test_duplicates_fail(self):
        with self.assertRaisesRegex(checker.ApplicationError, "duplicate ZIP entries"):
            self.read(self.entries() + [("backend.tex", b"duplicate")])

    def test_nonregular_entries_fail(self):
        base = [(name, value) for name, value in self.entries() if name != "backend.tex"]
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o644, stat.S_IFDIR | 0o755):
            info = zipfile.ZipInfo("backend.tex")
            info.create_system = 3
            info.external_attr = mode << 16
            with self.subTest(mode=mode), self.assertRaisesRegex(checker.ApplicationError, "not a regular file"):
                self.read(base + [(info, b"target")])

    def test_invalid_and_corrupt_archives_fail(self):
        payload = archive_bytes([(name, b"CRC_SENTINEL") for name in checker.ARCHIVE_FILES])
        index = payload.index(b"CRC_SENTINEL")
        corrupt = payload[:index] + b"X" + payload[index + 1:]
        for invalid in (b"not a zip", corrupt):
            with self.subTest(payload=invalid[:10]), self.assertRaisesRegex(checker.ApplicationError, "Cannot read"):
                self.read(payload=invalid)

    def test_extraction_rejects_unexpected_files_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            with self.assertRaisesRegex(checker.ApplicationError, "no files were written"):
                checker.write_project({"../outside": b"bad"}, project)
            self.assertFalse(project.exists())

    def test_nested_project_files_are_written_inside_destination(self):
        files = dict(self.entries())
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "folder with spaces"
            checker.write_project(files, project)
            for name, expected in files.items():
                self.assertEqual((project / name).read_bytes(), expected)


class SelectionTests(unittest.TestCase):
    def text(self, selection):
        return "\n".join(checker.BULLET_STARTS[name] for name in selection)

    def test_each_selection_uses_defined_bullets_once(self):
        self.assertEqual(set(checker.VARIANTS), set(checker.SELECTIONS))
        for selection in checker.SELECTIONS.values():
            self.assertEqual(len(selection), len(set(selection)))
            self.assertLessEqual(set(selection), set(checker.BULLET_STARTS))

    def test_correct_selection_and_order_pass(self):
        for selection in checker.SELECTIONS.values():
            checker.check_selection(self.text(selection), selection)

    def test_missing_duplicate_and_unselected_bullets_fail(self):
        selection = checker.SELECTIONS["backend"]
        for actual in (selection[:-1], selection + (selection[0],), selection + ("ToolRecovery",), selection + ("RoleFeature",)):
            with self.subTest(actual=actual), self.assertRaisesRegex(checker.ApplicationError, "occurrence"):
                checker.check_selection(self.text(actual), selection)

    def test_reordered_bullets_fail(self):
        selection = checker.SELECTIONS["backend"]
        with self.assertRaisesRegex(checker.ApplicationError, "entry-file order"):
            checker.check_selection(self.text(tuple(reversed(selection))), selection)

    def test_fixture_replacements_must_match_exactly_once(self):
        for value in (b"absent", b"old old"):
            files = {"source.tex": value}
            with self.assertRaisesRegex(checker.ApplicationError, "exactly one"):
                checker.replace_once(files, "source.tex", "old", "new")
            self.assertEqual(files["source.tex"], value)


class BuildFailureTests(unittest.TestCase):
    def test_latexmk_uses_project_config_without_shell_or_engine_override(self):
        result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "folder with spaces"
            project.mkdir()
            with patch.object(checker.shutil, "which", return_value="latexmk"), patch.object(checker.subprocess, "run", return_value=result) as run, patch.object(checker.check_pdf_text, "extract_text", return_value="PDF text"):
                checker.compile_project(project, "backend")
                self.assertEqual(run.call_args.args[0], ["latexmk", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "backend.tex"])
                self.assertEqual(run.call_args.kwargs["cwd"], project)
                self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_build_errors_timeouts_and_overfull_text_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            for result in (
                subprocess.CompletedProcess([], 1, stdout="compile error", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="Overfull \\hbox", stderr=""),
            ):
                with self.subTest(result=result), patch.object(checker.shutil, "which", return_value="latexmk"), patch.object(checker.subprocess, "run", return_value=result), self.assertRaises(checker.ApplicationError):
                    checker.compile_project(project, "backend")
            with patch.object(checker.shutil, "which", return_value="latexmk"), patch.object(checker.subprocess, "run", side_effect=subprocess.TimeoutExpired("latexmk", 180)), self.assertRaisesRegex(checker.ApplicationError, "Cannot compile"):
                checker.compile_project(project, "backend")

    def test_expected_failure_cannot_accept_success(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(checker.shutil, "which", return_value="latexmk"), patch.object(checker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")), self.assertRaisesRegex(checker.ApplicationError, "without an error"):
            checker.compile_project(Path(temporary), "backend", expect_failure=True)

    def test_missing_dependency_reports_failure(self):
        stderr = StringIO()
        with patch.object(checker.shutil, "which", return_value=None), redirect_stderr(stderr):
            self.assertEqual(checker.main([]), 1)
        self.assertIn("Install XeLaTeX, latexmk, and Poppler", stderr.getvalue())

    def test_published_mode_checks_requested_directory_without_compiling(self):
        with patch.object(checker.shutil, "which", return_value="pdftotext"), patch.object(checker, "check_published") as published, patch.object(checker, "compile_project") as compile_mock, redirect_stdout(StringIO()):
            self.assertEqual(checker.main(["--published", "--pdf-dir", "custom PDFs"]), 0)
            published.assert_called_once_with(Path("custom PDFs"))
            compile_mock.assert_not_called()

    def test_published_failure_returns_nonzero(self):
        with patch.object(checker.shutil, "which", return_value="pdftotext"), patch.object(checker, "check_published", side_effect=checker.check_pdf_text.CheckError("changed PDF")), redirect_stderr(StringIO()):
            self.assertEqual(checker.main(["--published"]), 1)


class BoundsTests(unittest.TestCase):
    def check(self, words, width=612, height=792):
        body = "".join(
            f'<word xMin="{left}" yMin="{top}" xMax="{right}" yMax="{bottom}">{label}</word>'
            for left, top, right, bottom, label in words
        )
        xml = f'<doc><page width="{width}" height="{height}">{body}</page></doc>'
        result = subprocess.CompletedProcess([], 0, stdout=xml, stderr="")
        with patch.object(checker.shutil, "which", return_value="pdftotext"), patch.object(checker.subprocess, "run", return_value=result):
            checker.check_bounds(Path("resume.pdf"))

    def test_existing_large_name_glyph_box_and_body_pass(self):
        self.check([(36, 32.4, 208, 62.3, "Name"), (36, 90, 100, 100, "Experience")])

    def test_body_cannot_use_name_margin_exception(self):
        with self.assertRaisesRegex(checker.ApplicationError, "outside margins"):
            self.check([(36, 32.4, 100, 42, "Body")])

    def test_clipping_overlap_empty_text_and_wrong_paper_fail(self):
        for words in (
            [(30, 90, 100, 100, "Clipped")],
            [(36, 90, 100, 100, "First"), (90, 90, 140, 100, "Second")],
            [],
        ):
            with self.subTest(words=words), self.assertRaises(checker.ApplicationError):
                self.check(words)
        with self.assertRaisesRegex(checker.ApplicationError, "paper size"):
            self.check([(36, 90, 100, 100, "Body")], width=595, height=842)


if __name__ == "__main__":
    unittest.main()
