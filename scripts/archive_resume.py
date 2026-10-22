#!/usr/bin/env python3
"""Save the exact PDF used for an application, with a date and SHA-256 receipt."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]


class ArchiveError(Exception):
    """The selected PDF could not be saved without risking an existing copy."""


def label_slug(label):
    if not label.strip() or not label.isprintable():
        raise ArchiveError("Use a company/role label without line breaks or control characters.")
    slug = "".join(char if char.isalnum() else "-" for char in label.lower())
    slug = re.sub("-+", "-", slug).strip("-")[:80].rstrip("-")
    while len(slug.encode("utf-8")) > 200:
        slug = slug[:-1]
    slug = slug.rstrip("-")
    if not slug:
        raise ArchiveError("Include a letter or number in the company/role label.")
    return slug


def archive_pdf(source, label):
    slug = label_slug(label)
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ArchiveError("Choose an existing PDF file, not a directory.")
    saved_at = datetime.now().astimezone()
    archive_root = ROOT / "submissions"
    if archive_root.resolve() != archive_root:
        raise ArchiveError("The submissions folder must not be a symlink or use a redirected parent.")
    destination = archive_root / f"{saved_at.date().isoformat()}-{slug}"
    pdf = destination / f"resume-{slug}.pdf"

    with source.open("rb") as original:
        before = os.fstat(original.fileno())
        if not re.match(rb"%PDF-\d\.\d(?:\r|\n)", original.read(10)):
            raise ArchiveError("This file has no PDF header. Choose the exported PDF, not a source file or download page.")
        original.seek(0)
        archive_root.mkdir(mode=0o700, exist_ok=True)
        try:
            destination.mkdir(mode=0o700)
        except FileExistsError as error:
            raise ArchiveError("An archive already exists for this date and label. Keep it and use a different label for another submission.") from error

        try:
            digest = hashlib.sha256()
            size = 0
            with pdf.open("xb") as copy:
                pdf.chmod(0o600)
                while chunk := original.read(1024 * 1024):
                    copy.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            after = os.fstat(original.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns
            ) or size != before.st_size:
                raise ArchiveError("The source changed while copying. Finish rebuilding or downloading it, then retry.")

            receipt = {
                "label": label.strip(),
                "saved_at": saved_at.isoformat(timespec="seconds"),
                "pdf": pdf.name,
                "bytes": size,
                "sha256": digest.hexdigest(),
            }
            receipt_path = destination / "receipt.json"
            with receipt_path.open("x", encoding="utf-8") as output:
                receipt_path.chmod(0o600)
                json.dump(receipt, output, ensure_ascii=False, indent=2)
                output.write("\n")
        except BaseException:
            # Only this invocation created the directory; never remove an older archive.
            shutil.rmtree(destination)
            raise
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Saves locally under this checkout's ignored submissions/ folder. "
            "Existing archives are never overwritten. Checks the PDF header only; "
            "review the PDF before archiving it. Requires Python 3.9+, no other tools."
        ),
    )
    parser.add_argument("pdf", type=Path, help="the exact PDF uploaded to the application")
    parser.add_argument("--label", required=True, help='company and role, for example "Acme - Backend Engineer"')
    args = parser.parse_args(argv)
    try:
        destination = archive_pdf(args.pdf, args.label)
    except (ArchiveError, OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        print("Check the file path, label, and folder permissions; existing archives are unchanged.", file=sys.stderr)
        return 1
    print(f"Saved: {destination}")
    print("The PDF and receipt are local. This records the file, not proof that an employer received it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
