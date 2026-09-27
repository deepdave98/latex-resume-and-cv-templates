#!/usr/bin/env python3
"""Compile the downloaded ZIP projects and check their PDF text. No pip packages."""

import argparse
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

import check_pdf_text


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ("new-grad", "no-internship", "experienced", "ai-engineer", "ml-engineer", "graduate-admissions")
ARCHIVE_FILES = frozenset({"resume.tex", "resume.cls", "latexmkrc", "START_HERE.md", "LICENSE"})


class StarterError(Exception):
    """A starter archive cannot be safely unpacked, compiled, or checked."""


def read_archive(path):
    """Validate every entry before returning any files for extraction."""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise StarterError(f"{path}: duplicate ZIP entries")
            if set(names) != ARCHIVE_FILES:
                missing = sorted(ARCHIVE_FILES - set(names))
                extra = sorted(set(names) - ARCHIVE_FILES)
                raise StarterError(
                    f"{path}: unexpected ZIP contents; missing={missing}, extra={extra}. "
                    "Run make downloads to rebuild the starter archives."
                )
            for entry in entries:
                mode = entry.external_attr >> 16
                if entry.is_dir() or (entry.external_attr & 0x10):
                    raise StarterError(f"{path}: directories are not allowed: {entry.filename}")
                if stat.S_ISLNK(mode):
                    raise StarterError(f"{path}: symlinks are not allowed: {entry.filename}")
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise StarterError(f"{path}: not a regular file: {entry.filename}")
                if entry.orig_filename != entry.filename:
                    raise StarterError(f"{path}: invalid ZIP filename: {entry.orig_filename!r}")
            # Reading everything also checks CRCs before creating project files.
            return {entry.filename: archive.read(entry) for entry in entries}
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise StarterError(
            f"Cannot read starter archive {path}: {error}. Run make downloads first."
        ) from error


def check_starter(archive, template, project_dir, latexmk):
    files = read_archive(archive)
    try:
        project_dir.mkdir()
        for name, content in files.items():
            (project_dir / name).write_bytes(content)
        subprocess.run(
            [latexmk, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except subprocess.CalledProcessError as error:
        detail = ((error.stdout or "") + "\n" + (error.stderr or "")).strip()
        excerpt = "\n".join(detail.splitlines()[-40:])
        raise StarterError(
            f"{archive}: latexmk failed. Check XeLaTeX and the bundled latexmkrc.\n{excerpt}"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise StarterError(f"{archive}: latexmk exceeded 180 seconds") from error
    except OSError as error:
        raise StarterError(f"Cannot build {archive}: {error}") from error

    try:
        check_pdf_text.check_pdf(project_dir / "resume.pdf", template)
    except check_pdf_text.CheckError as error:
        raise StarterError(f"{archive}: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads-dir", type=Path, default=ROOT / "downloads")
    args = parser.parse_args(argv)
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        print("FAIL: latexmk not found. Install a TeX distribution with XeLaTeX and latexmk.", file=sys.stderr)
        return 1

    failures = 0
    with tempfile.TemporaryDirectory(prefix="resume-starters-") as temporary:
        for template in TEMPLATES:
            archive = args.downloads_dir / f"{template}-resume.zip"
            folder = f"{template} project"
            try:
                check_starter(archive, template, Path(temporary) / folder, latexmk)
            except StarterError as error:
                print(f"FAIL: {error}", file=sys.stderr)
                failures += 1
            else:
                print(f"PASS: {archive} (standalone build and PDF text match)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
