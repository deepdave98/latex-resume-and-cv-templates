#!/usr/bin/env python3
"""Save a submitted PDF with a receipt, or verify a saved copy."""

import argparse
from datetime import datetime
import hashlib
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]


class ArchiveError(Exception):
    """An archive could not be saved or verified safely."""


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


def receipt_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ArchiveError("The receipt contains duplicate fields.")
        fields[key] = value
    return fields


def regular_file(path, description):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ArchiveError(f"{description} must be a regular file, not a symlink or directory.")


def verify_archive(directory):
    """Compare one local PDF with its receipt; never write or extract resume text."""
    try:
        directory = Path(directory).expanduser().resolve(strict=True)
        if not directory.is_dir():
            raise ArchiveError("Choose the archive folder containing receipt.json and its PDF.")
        receipt_path = directory / "receipt.json"
        regular_file(receipt_path, "The receipt")
        with receipt_path.open(encoding="utf-8") as source:
            receipt = json.load(source, object_pairs_hook=receipt_fields)
        if not isinstance(receipt, dict):
            raise ArchiveError("The receipt must be a JSON object.")
        name, size, expected = (receipt.get(key) for key in ("pdf", "bytes", "sha256"))
        if type(size) is not int or size <= 0:
            raise ArchiveError("The receipt needs a positive whole-number byte count.")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            raise ArchiveError("The receipt needs a 64-character SHA-256 hash.")
        reserved = getattr(ntpath, "isreserved", lambda value: PureWindowsPath(value).is_reserved())
        if (
            not isinstance(name, str) or not name or not name.isprintable()
            or any(char in name for char in '/\\:*?"<>|')
            or Path(name).suffix.lower() != ".pdf" or reserved(name)
        ):
            raise ArchiveError("The receipt must name one local PDF file, without a path.")
        pdf = directory / name
        regular_file(pdf, "The saved PDF")
        digest = hashlib.sha256()
        count = 0
        with pdf.open("rb") as source:
            before = os.fstat(source.fileno())
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                count += len(chunk)
            after = os.fstat(source.fileno())
        states = [
            (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            for info in (before, after, pdf.lstat())
        ]
        if states[0] != states[1] or states[1] != states[2]:
            raise ArchiveError("The saved PDF changed during verification. Finish editing or copying it, then retry.")
        if count != size:
            raise ArchiveError("The saved PDF's byte count does not match the receipt.")
        if digest.hexdigest() != expected.lower():
            raise ArchiveError("The saved PDF's SHA-256 hash does not match the receipt.")
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ArchiveError("The receipt is not readable JSON.") from error
    except (OSError, RuntimeError) as error:
        raise ArchiveError("Cannot read the archive folder, receipt, or PDF. Check their paths and permissions.") from error


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Saves locally under this checkout's ignored submissions/ folder. "
            "Existing archives are never overwritten. Checks the PDF header only; "
            "review the PDF before archiving it. Verification reads only the saved "
            "PDF and receipt, including in a moved backup folder. Requires Python 3.9+, no other tools."
        ),
    )
    parser.add_argument("pdf", type=Path, nargs="?", help="the exact PDF uploaded to the application")
    parser.add_argument("--label", help='company and role, for example "Acme - Backend Engineer"')
    parser.add_argument("--verify", type=Path, metavar="ARCHIVE_DIR", help="check the saved PDF against its receipt; change no files")
    args = parser.parse_args(argv)
    if args.verify is not None:
        if args.pdf is not None or args.label is not None:
            parser.error("Use --verify ARCHIVE_DIR without a PDF argument or --label.")
        try:
            verify_archive(args.verify)
        except ArchiveError as error:
            print(f"FAIL: {error}", file=sys.stderr)
            print("No files changed. Compare with a trusted backup before replacing either file.", file=sys.stderr)
            return 1
        print("PASS: the saved PDF's byte count and SHA-256 hash match its receipt.")
        print("No files changed. This is not a signature or proof that an employer received it.")
        return 0
    if args.pdf is None or args.label is None:
        parser.error("Choose a PDF and --label, or use --verify ARCHIVE_DIR.")
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
