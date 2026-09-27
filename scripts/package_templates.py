#!/usr/bin/env python3
"""Build the standalone starter downloads, or check that they match the source."""

import argparse
from io import BytesIO
from pathlib import Path
import stat
import sys
from zipfile import ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_SOURCES = {
    "new-grad": "templates/new-grad-resume.tex",
    "no-internship": "templates/no-internship-resume.tex",
    "experienced": "templates/experienced-resume.tex",
    "ai-engineer": "templates/ai-engineer-resume.tex",
    "ml-engineer": "templates/ml-engineer-resume.tex",
    "graduate-admissions": "templates/graduate-admissions-resume.tex",
}
SHARED_SOURCES = {
    "resume.cls": "resume.cls",
    "latexmkrc": "assets/starter/latexmkrc",
    "START_HERE.md": "assets/starter/START_HERE.md",
    "LICENSE": "LICENSE",
}


def starter_files(root, template):
    # Use an allowlist, never a directory walk: personal files and build logs
    # must not enter a public download.
    sources = {"resume.tex": TEMPLATE_SOURCES[template], **SHARED_SOURCES}
    files = {}
    for name, relative in sources.items():
        source = root / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Expected a regular source file: {source}")
        # Universal newlines keep the ZIP identical in CRLF and LF checkouts.
        files[name] = source.read_text(encoding="utf-8").encode("utf-8")
    return files


def archive_bytes(files):
    result = BytesIO()
    with ZipFile(result, "w", compression=ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            # These files are small. Stored entries avoid compression-version
            # differences so CI can compare the complete ZIP byte for byte.
            info.compress_type = ZIP_STORED
            archive.writestr(info, content)
    return result.getvalue()


def check_archive(path, expected_bytes):
    return not path.is_symlink() and path.is_file() and path.read_bytes() == expected_bytes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on missing or stale ZIPs; write nothing")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "downloads")
    args = parser.parse_args(argv)
    failures = 0
    for template in TEMPLATE_SOURCES:
        destination = args.output_dir / f"{template}-resume.zip"
        try:
            payload = archive_bytes(starter_files(ROOT, template))
            if args.check:
                if not check_archive(destination, payload):
                    print(f"FAIL: {destination} is missing or stale. Run make downloads.", file=sys.stderr)
                    failures += 1
                else:
                    print(f"PASS: {destination} matches its source")
            else:
                if destination.is_symlink():
                    raise ValueError(f"Refusing to replace a symlink: {destination}")
                args.output_dir.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
                print(f"Built {destination} ({len(payload):,} bytes)")
        except (OSError, UnicodeError, ValueError) as error:
            print(f"FAIL: {error}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
