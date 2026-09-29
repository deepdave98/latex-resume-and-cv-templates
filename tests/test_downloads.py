"""Starter packaging and failure tests; no TeX or Poppler required."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import warnings
import zipfile

import check_starter_builds as smoke


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_templates as packager


INPUTS = {
    "resume.cls": "\\ProvidesClass{resume}\n",
    "LICENSE": "Example license\n",
    "assets/starter/latexmkrc": "$pdf_mode = 5;\n",
    "assets/starter/START_HERE.md": "# Start here\nEdit resume.tex.\n",
}
EXPECTED_TEMPLATES = {
    "new-grad": "templates/new-grad-resume.tex",
    "no-internship": "templates/no-internship-resume.tex",
    "experienced": "templates/experienced-resume.tex",
    "ai-engineer": "templates/ai-engineer-resume.tex",
    "ml-engineer": "templates/ml-engineer-resume.tex",
    "graduate-admissions": "templates/graduate-admissions-resume.tex",
}


def fixture_root(path, newline="\n"):
    inputs = dict(INPUTS)
    for template, source in packager.TEMPLATE_SOURCES.items():
        inputs[source] = f"% {template}\n\\documentclass{{resume}}\n"
    for name, text in inputs.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return inputs


def fixture_archive(entries=None):
    entries = entries if entries is not None else [(name, name.encode()) for name in sorted(smoke.ARCHIVE_FILES)]
    output = BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        warnings.simplefilter("ignore", UserWarning)
        for name, content in entries:
            info = name if isinstance(name, zipfile.ZipInfo) else zipfile.ZipInfo(name)
            if not isinstance(name, zipfile.ZipInfo):
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, content)
    return output.getvalue()


class PackagingTests(unittest.TestCase):
    def test_template_registries_cover_all_starters(self):
        self.assertEqual(packager.TEMPLATE_SOURCES, EXPECTED_TEMPLATES)
        self.assertEqual(smoke.TEMPLATES, tuple(EXPECTED_TEMPLATES))
        self.assertEqual(set(smoke.TEMPLATES), set(smoke.check_pdf_text.PAGE_COUNTS))

    def test_archive_is_deterministic_and_sorted(self):
        files = {"resume.tex": b"source", "LICENSE": b"license", "resume.cls": b"class"}
        first = packager.archive_bytes(files)
        self.assertEqual(first, packager.archive_bytes(dict(reversed(list(files.items())))))
        with zipfile.ZipFile(BytesIO(first)) as archive:
            self.assertEqual(archive.namelist(), sorted(files))
            for entry in archive.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(entry.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(stat.S_IMODE(entry.external_attr >> 16), 0o644)
                self.assertTrue(stat.S_ISREG(entry.external_attr >> 16))
                self.assertEqual(archive.read(entry), files[entry.filename])

    def test_archive_content_matches_current_sources(self):
        shared = {
            "resume.cls": "resume.cls",
            "LICENSE": "LICENSE",
            "latexmkrc": "assets/starter/latexmkrc",
            "START_HERE.md": "assets/starter/START_HERE.md",
        }
        for template, source in packager.TEMPLATE_SOURCES.items():
            with self.subTest(template=template):
                files = packager.starter_files(packager.ROOT, template)
                self.assertEqual(set(files), smoke.ARCHIVE_FILES)
                with zipfile.ZipFile(BytesIO(packager.archive_bytes(files))) as archive:
                    for name, source_path in {**shared, "resume.tex": source}.items():
                        expected = (packager.ROOT / source_path).read_text(encoding="utf-8").encode("utf-8")
                        self.assertEqual(archive.read(name), expected)

    def test_source_mtimes_do_not_change_archive_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = fixture_root(root)
            before = packager.archive_bytes(packager.starter_files(root, "new-grad"))
            for name in inputs:
                os.utime(root / name, (1700000000, 1700000000))
            self.assertEqual(before, packager.archive_bytes(packager.starter_files(root, "new-grad")))

    def test_crlf_and_lf_checkouts_produce_identical_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_root(root / "lf")
            fixture_root(root / "crlf", newline="\r\n")
            for template in packager.TEMPLATE_SOURCES:
                with self.subTest(template=template):
                    self.assertEqual(
                        packager.archive_bytes(packager.starter_files(root / "lf", template)),
                        packager.archive_bytes(packager.starter_files(root / "crlf", template)),
                    )

    def test_unrelated_and_private_files_are_not_packaged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_root(root)
            (root / ".context").mkdir()
            (root / ".context" / "private.txt").write_bytes(b"PRIVATE_SENTINEL")
            (root / "my-resume.tex").write_bytes(b"PRIVATE_SENTINEL")
            for template in packager.TEMPLATE_SOURCES:
                files = packager.starter_files(root, template)
                self.assertEqual(set(files), smoke.ARCHIVE_FILES)
                self.assertNotIn(b"PRIVATE_SENTINEL", b"".join(files.values()))

    def test_selected_source_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_root(root)
            target = root / "resume.cls"
            target.unlink()
            try:
                target.symlink_to(root / "LICENSE")
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symlinks unavailable: {error}")
            with self.assertRaises((OSError, ValueError)):
                packager.starter_files(root, "new-grad")

    def test_check_archive_rejects_missing_stale_and_corrupt_without_writes(self):
        expected = packager.archive_bytes({"resume.tex": b"current"})
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "resume.zip"
            self.assertFalse(packager.check_archive(archive, expected))
            self.assertFalse(archive.exists())
            for content in (b"not a zip", packager.archive_bytes({"resume.tex": b"old"}), expected):
                with self.subTest(content=content[:20]):
                    archive.write_bytes(content)
                    before = archive.stat().st_mtime_ns
                    self.assertEqual(packager.check_archive(archive, expected), content == expected)
                    self.assertEqual(archive.read_bytes(), content)
                    self.assertEqual(archive.stat().st_mtime_ns, before)

    def test_check_archive_rejects_symlink(self):
        expected = packager.archive_bytes({"resume.tex": b"current"})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "target.zip").write_bytes(expected)
            try:
                (root / "link.zip").symlink_to(root / "target.zip")
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"Symlinks unavailable: {error}")
            self.assertFalse(packager.check_archive(root / "link.zip", expected))

    def test_check_cli_fails_missing_then_passes_current_and_fails_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "download folder"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(packager.main(["--check", "--output-dir", str(output)]), 1)
                self.assertFalse(output.exists())
                self.assertEqual(packager.main(["--output-dir", str(output)]), 0)
                self.assertEqual(packager.main(["--check", "--output-dir", str(output)]), 0)
                for template in EXPECTED_TEMPLATES:
                    self.assertTrue((output / f"{template}-resume.zip").is_file())
                archive = output / "new-grad-resume.zip"
                archive.write_bytes(b"stale")
                self.assertEqual(packager.main(["--check", "--output-dir", str(output)]), 1)
                self.assertEqual(archive.read_bytes(), b"stale")


class ReadmeDownloadTests(unittest.TestCase):
    def setUp(self):
        readme = (packager.ROOT / "README.md").read_text(encoding="utf-8")
        self.links = re.findall(r"\]\((https://[^\s)]+)\)", readme)
        self.downloads = [
            f"https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/{template}-resume.zip"
            for template in packager.TEMPLATE_SOURCES
        ]
        self.application_download = "https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/application-versions.zip"

    def test_overleaf_buttons_import_each_current_zip_with_xelatex(self):
        imports = []
        for link in self.links:
            url = urlsplit(link)
            if url.netloc != "www.overleaf.com" or url.path != "/docs":
                continue
            params = parse_qs(url.query, keep_blank_values=True)
            self.assertEqual(params.get("engine"), ["xelatex"])
            self.assertEqual(len(params.get("snip_uri", [])), 1)
            main_document = "backend.tex" if params["snip_uri"] == [self.application_download] else "resume.tex"
            self.assertEqual(params.get("main_document"), [main_document])
            imports.extend(params["snip_uri"])
        self.assertCountEqual(imports, self.downloads + [self.application_download])

    def test_readme_links_directly_to_each_current_zip_once(self):
        for download in self.downloads:
            with self.subTest(download=download):
                self.assertEqual(self.links.count(download), 1)

    def test_application_project_links_preserve_one_shared_overleaf_project(self):
        self.assertEqual(self.links.count(self.application_download), 1)
        guide = (packager.ROOT / "examples/application-versions/README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((https://[^\s)]+)\)", guide)
        self.assertEqual(links.count(self.application_download), 1)
        imports = [urlsplit(link) for link in links if urlsplit(link).netloc == "www.overleaf.com" and urlsplit(link).path == "/docs"]
        self.assertEqual(len(imports), 1)
        self.assertEqual(parse_qs(imports[0].query), {
            "snip_uri": [self.application_download],
            "engine": ["xelatex"],
            "main_document": ["backend.tex"],
        })


class StarterArchiveTests(unittest.TestCase):
    def read(self, content):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "starter.zip"
            archive.write_bytes(content)
            return smoke.read_archive(archive)

    def test_valid_archive_has_exact_files_and_bytes(self):
        self.assertEqual(self.read(fixture_archive()), {name: name.encode() for name in smoke.ARCHIVE_FILES})

    def test_missing_and_extra_entries_fail(self):
        base = [(name, b"text") for name in sorted(smoke.ARCHIVE_FILES)]
        for entries in (base[:-1], base + [(".context/private.txt", b"secret")]):
            with self.subTest(entries=entries), self.assertRaisesRegex(smoke.StarterError, "unexpected ZIP contents"):
                self.read(fixture_archive(entries))

    def test_path_traversal_and_absolute_paths_fail_before_extraction(self):
        base = [(name, b"text") for name in smoke.ARCHIVE_FILES if name != "resume.tex"]
        for name in ("../resume.tex", "/resume.tex", "nested/resume.tex", "..\\resume.tex", "C:\\resume.tex"):
            with self.subTest(name=name), self.assertRaisesRegex(smoke.StarterError, "unexpected ZIP contents"):
                self.read(fixture_archive(base + [(name, b"text")]))

    def test_duplicate_entries_fail(self):
        entries = [(name, b"text") for name in smoke.ARCHIVE_FILES] + [("resume.tex", b"duplicate")]
        with self.assertRaisesRegex(smoke.StarterError, "duplicate ZIP entries"):
            self.read(fixture_archive(entries))

    def test_symlink_and_other_file_types_fail(self):
        base = [(name, b"text") for name in smoke.ARCHIVE_FILES if name != "resume.tex"]
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o644, stat.S_IFDIR | 0o755):
            info = zipfile.ZipInfo("resume.tex")
            info.create_system = 3
            info.external_attr = mode << 16
            with self.subTest(mode=mode), self.assertRaises(smoke.StarterError):
                self.read(fixture_archive(base + [(info, b"target")]))

    def test_invalid_zip_and_crc_failure_are_actionable(self):
        payload = b"unique payload to corrupt"
        valid = fixture_archive([(name, payload) for name in smoke.ARCHIVE_FILES])
        # Change stored payload bytes while retaining its recorded CRC.
        location = valid.index(payload)
        corrupt = valid[:location] + b"X" + valid[location + 1:]
        for content in (b"not a zip", corrupt):
            with self.subTest(content=content[:20]), self.assertRaisesRegex(smoke.StarterError, "Cannot read starter archive"):
                self.read(content)


class StarterBuildTests(unittest.TestCase):
    def test_build_uses_only_archive_files_and_bundled_engine_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "starter.zip"
            archive.write_bytes(fixture_archive())
            project = root / "project with spaces"
            with patch.object(smoke.subprocess, "run") as run, patch.object(smoke.check_pdf_text, "check_pdf") as check:
                smoke.check_starter(archive, "new-grad", project, "/bin/latexmk")
                self.assertEqual(set(path.name for path in project.iterdir()), smoke.ARCHIVE_FILES)
                self.assertEqual(run.call_args.args[0], ["/bin/latexmk", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"])
                self.assertEqual(run.call_args.kwargs["cwd"], project)
                self.assertFalse(run.call_args.kwargs.get("shell", False))
                check.assert_called_once_with(project / "resume.pdf", "new-grad")

    def test_invalid_archive_does_not_create_project_or_run_tex(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "starter.zip"
            archive.write_bytes(b"not a zip")
            with patch.object(smoke.subprocess, "run") as run, self.assertRaises(smoke.StarterError):
                smoke.check_starter(archive, "new-grad", root / "project", "latexmk")
            self.assertFalse((root / "project").exists())
            run.assert_not_called()

    def test_compiler_failure_includes_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "starter.zip"
            archive.write_bytes(fixture_archive())
            error = subprocess.CalledProcessError(1, "latexmk", output="Missing font example")
            with patch.object(smoke.subprocess, "run", side_effect=error):
                with self.assertRaisesRegex(smoke.StarterError, "Missing font example"):
                    smoke.check_starter(archive, "new-grad", root / "project", "latexmk")

    def test_cli_missing_latexmk_is_actionable(self):
        output = StringIO()
        with patch.object(smoke.shutil, "which", return_value=None), redirect_stderr(output):
            self.assertEqual(smoke.main([]), 1)
        self.assertIn("Install a TeX distribution", output.getvalue())

    def test_cli_checks_all_archives_in_separate_temporary_projects(self):
        projects = []

        def build(archive, template, project, latexmk):
            project.mkdir()
            projects.append(project)
            if template == "new-grad":
                raise smoke.StarterError("failed build")

        with patch.object(smoke.shutil, "which", return_value="latexmk"):
            with patch.object(smoke, "check_starter", side_effect=build) as check:
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertEqual(smoke.main(["--downloads-dir", "custom downloads"]), 1)
                self.assertEqual(check.call_count, len(EXPECTED_TEMPLATES))
        self.assertEqual(len(projects), len(EXPECTED_TEMPLATES))
        self.assertEqual(len(set(projects)), len(EXPECTED_TEMPLATES))
        self.assertTrue(all(" " in path.name for path in projects))
        self.assertTrue(all(not path.exists() for path in projects))


if __name__ == "__main__":
    unittest.main()
