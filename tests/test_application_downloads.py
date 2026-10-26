"""The optional application-version ZIP is deterministic and allowlisted."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_application_versions as packager


EXPECTED_SOURCES = {
    "resume.tex": "examples/application-versions/resume.tex",
    "backend.tex": "examples/application-versions/backend.tex",
    "setup.tex": "examples/application-versions/setup.tex",
    "latexmkrc": "examples/application-versions/latexmkrc",
    "README.md": "examples/application-versions/README.md",
    "content/profile.tex": "examples/application-versions/content/profile.tex",
    "content/projects.tex": "examples/application-versions/content/projects.tex",
    "content/experience.tex": "examples/application-versions/content/experience.tex",
    "content/education.tex": "examples/application-versions/content/education.tex",
    "content/skills.tex": "examples/application-versions/content/skills.tex",
    "resume.cls": "resume.cls",
    "LICENSE": "LICENSE",
}


def fixture_root(root, newline="\n"):
    for name, relative in EXPECTED_SOURCES.items():
        source = root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(f"% {name}\nUTF-8: résumé\n".replace("\n", newline).encode("utf-8"))


class ApplicationDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "source tree with spaces"
        fixture_root(self.root)
        self.output = Path(self.temporary.name).resolve() / "download folder"
        self.archive = self.output / "application-versions.zip"

    def run_main(self, *args):
        self.stdout, self.stderr = StringIO(), StringIO()
        with patch.object(packager, "ROOT", self.root), redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            return packager.main(["--output-dir", str(self.output), *args])

    def symlink(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks unavailable: {error}")

    def test_allowlist_names_all_project_sources_and_only_shared_class_and_license(self):
        self.assertEqual(packager.SOURCES, EXPECTED_SOURCES)
        self.assertEqual(packager.ARCHIVE_NAME, "application-versions.zip")

    def test_archive_has_exact_source_bytes_and_portable_metadata(self):
        files = packager.project_files(self.root)
        payload = packager.archive_bytes(files)
        with ZipFile(BytesIO(payload)) as archive:
            self.assertEqual(archive.namelist(), sorted(EXPECTED_SOURCES))
            for entry in archive.infolist():
                self.assertEqual(archive.read(entry), (self.root / EXPECTED_SOURCES[entry.filename]).read_bytes())
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(entry.create_system, 3)
                self.assertEqual(entry.compress_type, ZIP_STORED)
                self.assertTrue(stat.S_ISREG(entry.external_attr >> 16))
                self.assertEqual(stat.S_IMODE(entry.external_attr >> 16), 0o644)

    def test_source_mtimes_and_dict_order_do_not_change_archive(self):
        files = packager.project_files(self.root)
        expected = packager.archive_bytes(files)
        for relative in EXPECTED_SOURCES.values():
            os.utime(self.root / relative, (1700000000, 1700000000))
        self.assertEqual(expected, packager.archive_bytes(packager.project_files(self.root)))
        self.assertEqual(expected, packager.archive_bytes(dict(reversed(list(files.items())))))

    def test_crlf_and_lf_sources_produce_identical_archive(self):
        crlf = Path(self.temporary.name) / "windows checkout"
        fixture_root(crlf, newline="\r\n")
        self.assertEqual(
            packager.archive_bytes(packager.project_files(self.root)),
            packager.archive_bytes(packager.project_files(crlf)),
        )

    def test_private_sources_pdfs_logs_and_hidden_files_are_never_added(self):
        private_paths = (
            ".context/private.txt",
            "my-resume.tex",
            "examples/application-versions/personal.tex",
            "examples/application-versions/backend.pdf",
            "examples/application-versions/backend.log",
            "examples/application-versions/.env",
            "examples/application-versions/content/private.tex",
            "examples/application-versions/content/old-resume.pdf",
        )
        for relative in private_paths:
            private = self.root / relative
            private.parent.mkdir(parents=True, exist_ok=True)
            private.write_bytes(b"PRIVATE_SENTINEL")
        files = packager.project_files(self.root)
        self.assertEqual(set(files), set(EXPECTED_SOURCES))
        self.assertNotIn(b"PRIVATE_SENTINEL", packager.archive_bytes(files))

    def test_missing_source_fails_before_creating_download_folder(self):
        (self.root / EXPECTED_SOURCES["backend.tex"]).unlink()
        self.assertEqual(self.run_main(), 1)
        self.assertIn("Expected a regular source file", self.stderr.getvalue())
        self.assertFalse(self.output.exists())

    def test_source_directory_instead_of_file_is_rejected(self):
        source = self.root / EXPECTED_SOURCES["content/profile.tex"]
        source.unlink()
        source.mkdir()
        with self.assertRaisesRegex(ValueError, "regular source file"):
            packager.project_files(self.root)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Named pipes unavailable")
    def test_nonregular_source_is_rejected_without_reading(self):
        source = self.root / "LICENSE"
        source.unlink()
        os.mkfifo(source)
        with self.assertRaisesRegex(ValueError, "regular source file"):
            packager.project_files(self.root)

    def test_non_utf8_source_fails_without_creating_archive(self):
        (self.root / "LICENSE").write_bytes(b"\xff\xfe")
        self.assertEqual(self.run_main(), 1)
        self.assertIn("FAIL:", self.stderr.getvalue())
        self.assertFalse(self.output.exists())

    def test_leaf_source_symlink_is_rejected_even_with_valid_target(self):
        source = self.root / "resume.cls"
        source.unlink()
        self.symlink(source, self.root / "LICENSE")
        with self.assertRaisesRegex(ValueError, "source symlink"):
            packager.project_files(self.root)

    def test_broken_source_symlink_is_rejected(self):
        source = self.root / "LICENSE"
        source.unlink()
        self.symlink(source, self.root / "missing")
        self.assertEqual(self.run_main(), 1)
        self.assertIn("source symlink", self.stderr.getvalue())
        self.assertFalse(self.output.exists())

    def test_ancestor_source_symlink_is_rejected(self):
        for relative in ("examples", "examples/application-versions", "examples/application-versions/content"):
            with self.subTest(relative=relative):
                source = self.root / relative
                moved = source.with_name(source.name + "-real")
                source.rename(moved)
                self.symlink(source, moved)
                try:
                    with self.assertRaisesRegex(ValueError, "source symlink"):
                        packager.project_files(self.root)
                finally:
                    source.unlink()
                    moved.rename(source)

    def test_symlink_root_is_rejected(self):
        link = self.root.with_name("linked source")
        self.symlink(link, self.root)
        with self.assertRaisesRegex(ValueError, "regular source directory"):
            packager.project_files(link)

    def test_check_missing_is_read_only(self):
        with patch.object(Path, "mkdir", side_effect=AssertionError("check attempted mkdir")), patch.object(
            Path, "write_bytes", side_effect=AssertionError("check attempted a write")
        ):
            self.assertEqual(self.run_main("--check"), 1)
        self.assertFalse(self.output.exists())
        self.assertIn("missing or stale", self.stderr.getvalue())

    def test_check_current_and_stale_preserves_bytes_and_mtime(self):
        self.assertEqual(self.run_main(), 0)
        current = self.archive.read_bytes()
        for content, status in ((current, 0), (b"old or corrupt zip", 1)):
            with self.subTest(status=status):
                self.archive.write_bytes(content)
                before = self.archive.stat().st_mtime_ns
                self.assertEqual(self.run_main("--check"), status)
                self.assertEqual(self.archive.read_bytes(), content)
                self.assertEqual(self.archive.stat().st_mtime_ns, before)

    def test_source_change_requires_new_archive(self):
        self.assertEqual(self.run_main(), 0)
        old_archive = self.archive.read_bytes()
        source = self.root / EXPECTED_SOURCES["content/experience.tex"]
        source.write_bytes(b"changed experience\n")
        self.assertEqual(self.run_main("--check"), 1)
        self.assertEqual(self.archive.read_bytes(), old_archive)
        self.assertEqual(self.run_main(), 0)
        self.assertNotEqual(self.archive.read_bytes(), old_archive)
        self.assertEqual(self.run_main("--check"), 0)

    def test_custom_output_with_spaces_contains_only_one_download(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual([path.name for path in self.output.iterdir()], ["application-versions.zip"])
        self.assertIn("Built", self.stdout.getvalue())
        self.assertEqual(self.run_main("--check"), 0)

    def test_existing_other_downloads_are_untouched(self):
        self.output.mkdir()
        existing = self.output / "new-grad-resume.zip"
        existing.write_bytes(b"do not touch")
        before = existing.stat().st_mtime_ns
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(existing.read_bytes(), b"do not touch")
        self.assertEqual(existing.stat().st_mtime_ns, before)

    def test_symlink_destination_never_overwrites_target(self):
        self.output.mkdir()
        target = Path(self.temporary.name) / "keep.zip"
        target.write_bytes(b"do not touch")
        self.symlink(self.archive, target)
        for args in ((), ("--check",)):
            with self.subTest(args=args):
                self.assertEqual(self.run_main(*args), 1)
                self.assertIn("symlink destination", self.stderr.getvalue())
                self.assertEqual(target.read_bytes(), b"do not touch")
                self.assertTrue(self.archive.is_symlink())

    def test_symlink_output_directory_is_rejected(self):
        actual_output = Path(self.temporary.name) / "actual output"
        actual_output.mkdir()
        self.symlink(self.output, actual_output)
        self.assertEqual(self.run_main(), 1)
        self.assertEqual(list(actual_output.iterdir()), [])

    def test_output_parent_symlink_preserves_existing_archive_and_creates_nothing(self):
        self.assertEqual(self.run_main(), 0)
        previous = self.archive.read_bytes()
        before = self.archive.stat().st_mtime_ns
        redirect = self.root / "redirect"
        self.symlink(redirect, self.output.parent)
        for target in (redirect / self.output.name, redirect / "missing" / "downloads"):
            with self.subTest(target=target), patch.object(self, "output", target):
                for args in ((), ("--check",)):
                    self.assertEqual(self.run_main(*args), 1)
                    self.assertIn("symlink destination", self.stderr.getvalue())
        self.assertEqual(self.archive.read_bytes(), previous)
        self.assertEqual(self.archive.stat().st_mtime_ns, before)
        self.assertFalse((self.output.parent / "missing").exists())

    def test_filesystem_errors_are_reported_without_traceback(self):
        with patch("package_templates.os.replace", side_effect=PermissionError("write denied")):
            self.assertEqual(self.run_main(), 1)
        self.assertEqual(self.stderr.getvalue().strip(), "FAIL: write denied")
        self.assertEqual(list(self.output.iterdir()), [])

    def test_failed_replacement_keeps_previous_archive_and_removes_temporary_file(self):
        self.assertEqual(self.run_main(), 0)
        previous = self.archive.read_bytes()
        before = self.archive.stat().st_mtime_ns
        (self.root / EXPECTED_SOURCES["README.md"]).write_text("A changed guide.\n", encoding="utf-8")
        with patch("package_templates.os.replace", side_effect=PermissionError("replacement denied")):
            self.assertEqual(self.run_main(), 1)
        self.assertEqual(self.archive.read_bytes(), previous)
        self.assertEqual(self.archive.stat().st_mtime_ns, before)
        self.assertEqual(list(self.output.iterdir()), [self.archive])

    def test_cli_help_and_invalid_argument_exit_codes(self):
        script = Path(packager.__file__)
        help_result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--check", help_result.stdout)
        bad_result = subprocess.run([sys.executable, str(script), "--not-a-real-option"], capture_output=True, text=True)
        self.assertEqual(bad_result.returncode, 2)
        self.assertIn("unrecognized arguments", bad_result.stderr)


if __name__ == "__main__":
    unittest.main()
