#!/usr/bin/env python3
"""Build the optional shared-content project, or check its download without writing."""

import argparse
from pathlib import Path
import sys

from package_templates import archive_bytes, check_archive


ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_NAME = "application-versions.zip"
# Keep this explicit. A directory walk could publish someone's private resume,
# an old PDF, or a build log alongside the example.
SOURCES = {
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


def project_files(root):
    """Read only the named UTF-8 sources, refusing links within the project."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Expected a regular source directory: {root}")
    files = {}
    for name, relative in SOURCES.items():
        source = root
        for part in Path(relative).parts:
            source /= part
            if source.is_symlink():
                raise ValueError(f"Refusing a source symlink: {source}")
        if not source.is_file():
            raise ValueError(f"Expected a regular source file: {source}")
        # Universal newlines keep Windows and Unix checkouts byte-identical.
        files[name] = source.read_text(encoding="utf-8").encode("utf-8")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on a missing or stale ZIP; write nothing")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "downloads")
    args = parser.parse_args(argv)
    destination = args.output_dir / ARCHIVE_NAME
    try:
        payload = archive_bytes(project_files(ROOT))
        if args.output_dir.is_symlink() or destination.is_symlink():
            raise ValueError(f"Refusing a symlink destination: {destination}")
        if args.check:
            if not check_archive(destination, payload):
                print(
                    f"FAIL: {destination} is missing or stale. Run make application-download.",
                    file=sys.stderr,
                )
                return 1
            print(f"PASS: {destination} matches its source")
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            print(f"Built {destination} ({len(payload):,} bytes)")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
