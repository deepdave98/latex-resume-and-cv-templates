#!/usr/bin/env python3
"""Check a personal PDF for basic text-extraction failures, without a baseline."""

import argparse
from decimal import Decimal
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata


EXTRACTION_TIMEOUT = 30


class CheckError(Exception):
    """A failed check, with a message that does not contain resume text."""


def extract_text(pdf, max_bytes=None):
    """Run Poppler locally. Never include its output in error messages."""
    try:
        resolved = pdf.expanduser().resolve(strict=True)
        if not resolved.is_file():
            raise CheckError("Input is not a file. Choose a PDF.")
        # Check readability before starting Poppler; an empty file is not a PDF.
        with resolved.open("rb") as source:
            if not source.read(1):
                raise CheckError("The input file is empty.")
        size = resolved.stat().st_size
        if max_bytes is not None and size > max_bytes:
            raise CheckError(f"File size is {size:,} bytes; limit {max_bytes:,} bytes.")
    except FileNotFoundError as error:
        raise CheckError("PDF not found. Check the file path.") from error
    except (OSError, RuntimeError, ValueError) as error:
        raise CheckError("Cannot read the input file. Check its path and permissions.") from error

    executable = shutil.which("pdftotext")
    if executable is None:
        raise CheckError("pdftotext not found. Install Poppler and add it to PATH.")
    try:
        result = subprocess.run(
            [executable, "-layout", "-enc", "UTF-8", str(resolved), "-"],
            check=True, capture_output=True, encoding="utf-8",
            timeout=EXTRACTION_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise CheckError("Text extraction timed out after 30 seconds.") from error
    except subprocess.CalledProcessError as error:
        raise CheckError(
            "pdftotext could not read this PDF. Check that it opens and is not password-protected."
        ) from error
    except UnicodeError as error:
        raise CheckError("pdftotext returned invalid UTF-8 text.") from error
    except OSError as error:
        raise CheckError("Could not run pdftotext. Check the Poppler installation.") from error
    if result.stderr.strip():
        raise CheckError("pdftotext reported a warning. Inspect the PDF and its extracted text.")
    return result.stdout


def split_pages(text):
    # Poppler ends each page with a form feed. Remove only its final separator;
    # two trailing separators still mean a blank last page, which must fail.
    pages = text.split("\f")
    if not pages[-1].strip():
        pages.pop()
    return pages


def check_text(text, max_pages=None):
    """Return the page count, or a specific failure without quoting the text."""
    pages = split_pages(text)
    if not pages:
        raise CheckError("No extractable text. Image-only PDFs need a text layer.")
    if max_pages is not None and len(pages) > max_pages:
        raise CheckError(f"Found {len(pages)} pages; the chosen limit is {max_pages}.")

    for number, page in enumerate(pages, start=1):
        for char in page:
            category = unicodedata.category(char)
            if char == "\ufffd" or (
                category in {"Cc", "Cs", "Co", "Cn"} and char not in "\n\r\t"
            ):
                raise CheckError(
                    f"Page {number}: replacement, unmapped, or control character U+{ord(char):04X}."
                )
        # Format characters can be valid in some writing systems. They do not
        # count as page content on their own, but do not reject them in words.
        if not any(
            not char.isspace() and not unicodedata.category(char).startswith("C")
            for char in page
        ):
            raise CheckError(f"Page {number} has no extractable text.")
    return len(pages)


def check_pdf(pdf, max_pages=None, max_bytes=None):
    return check_text(extract_text(pdf, max_bytes=max_bytes), max_pages=max_pages)


def megabyte_limit(value):
    message = "Use a positive decimal MB value of at least 0.000001 (one byte)."
    if len(value) > 32 or not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", value):
        raise argparse.ArgumentTypeError(message)
    numerator, denominator = Decimal(value).as_integer_ratio()
    # Compare whole bytes without binary floats or Decimal context rounding.
    limit = numerator * 1_000_000 // denominator
    if limit < 1:
        raise argparse.ArgumentTypeError(message)
    return limit


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a positive whole number.") from error
    if number < 1:
        raise argparse.ArgumentTypeError("Use a positive whole number.")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Runs locally; no uploads, saved text, or resume contents in the output. "
            "Does not check layout, reading order, missing words, claims, or ATS compatibility. "
            "Use -- before a filename that starts with a dash."
        ),
    )
    parser.add_argument("pdf", type=Path, help="path to your exported PDF")
    parser.add_argument(
        "--max-pages", type=positive_integer, metavar="N",
        help="fail above this page count; no limit by default",
    )
    parser.add_argument(
        "--max-size-mb", type=megabyte_limit, dest="max_bytes", metavar="MB",
        help="fail above this file size; 1 MB = 1,000,000 bytes; no limit by default",
    )
    args = parser.parse_args(argv)
    try:
        pages = check_pdf(args.pdf, max_pages=args.max_pages, max_bytes=args.max_bytes)
    except CheckError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    label = "page" if pages == 1 else "pages"
    print(f"PASS: {pages} {label}; text found on every page; no flagged characters.")
    if args.max_bytes is not None:
        print(f"File size is within the {args.max_bytes:,}-byte limit.")
    print("Extraction only. Review the PDF and its text before sending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
