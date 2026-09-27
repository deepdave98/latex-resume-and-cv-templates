#!/usr/bin/env python3
"""Check each PDF page against reviewed, layout-order text. No pip packages needed."""

import argparse
import difflib
from pathlib import Path
import shutil
import subprocess
import sys
import unicodedata


EXPECTED_DIR = Path(__file__).resolve().parent / "expected"
PAGE_COUNTS = {
    "new-grad": 1, "no-internship": 1, "experienced": 2,
    "ai-engineer": 1, "ml-engineer": 1, "graduate-admissions": 1,
}


class CheckError(Exception):
    """An unreadable PDF, missing dependency, or changed text snapshot."""


def split_pages(text):
    # Poppler terminates each page with a form feed. Drop its final separator,
    # but preserve an extra blank page so a layout overflow cannot pass.
    pages = text.split("\f")
    if not pages[-1].strip():
        pages.pop()
    return pages


def words(text):
    # Font ligatures (e.g. fi) and whitespace differ between PDF readers.
    # Keep punctuation, bullet markers, and line-end hyphens in the comparison.
    return unicodedata.normalize("NFKC", text).split()


def compare_pages(label, text, expected):
    pages = split_pages(text)
    if len(pages) != len(expected):
        raise CheckError(f"{label}: expected {len(expected)} pages, got {len(pages)}")

    for number, (actual, baseline) in enumerate(zip(pages, expected), start=1):
        if not actual.strip():
            raise CheckError(f"{label}, page {number}: no extractable text")
        for char in actual:
            if char == "\ufffd" or (
                unicodedata.category(char).startswith("C") and char not in "\n\r\t"
            ):
                raise CheckError(
                    f"{label}, page {number}: unmapped or control character U+{ord(char):04X}"
                )
        if not baseline.strip():
            raise CheckError(f"{label}, page {number}: empty text baseline")
        if words(actual) != words(baseline):
            diff = list(difflib.unified_diff(
                words(baseline), words(actual),
                fromfile="expected", tofile="extracted", lineterm="", n=3,
            ))
            excerpt = "\n".join(diff[:60])
            if len(diff) > 60:
                excerpt += "\n... diff truncated"
            raise CheckError(f"{label}, page {number}: extracted text changed\n{excerpt}")


def extract_text(pdf):
    if not pdf.is_file():
        raise CheckError(f"PDF not found: {pdf}. Build the templates first.")
    executable = shutil.which("pdftotext")
    if executable is None:
        raise CheckError("pdftotext not found. Install Poppler and add it to PATH.")
    try:
        result = subprocess.run(
            [executable, "-layout", "-enc", "UTF-8", str(pdf.resolve()), "-"],
            check=True, capture_output=True, encoding="utf-8", timeout=30,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "").strip()
        raise CheckError(f"pdftotext failed for {pdf}: {detail}") from error
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        raise CheckError(f"Cannot extract {pdf}: {error}") from error
    return result.stdout


def check_pdf(pdf, template):
    expected = []
    for page in range(1, PAGE_COUNTS[template] + 1):
        fixture = EXPECTED_DIR / f"{template}-{page}.txt"
        try:
            expected.append(fixture.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            raise CheckError(f"Cannot read baseline {fixture}: {error}") from error
    compare_pages(str(pdf), extract_text(pdf), expected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for template in PAGE_COUNTS:
        parser.add_argument(
            f"--{template}", type=Path,
            default=Path(f"build/{template}/{template}-resume.pdf"),
        )
    args = parser.parse_args(argv)
    failures = 0
    for template in PAGE_COUNTS:
        pdf = getattr(args, template.replace("-", "_"))
        try:
            check_pdf(pdf, template)
        except CheckError as error:
            print(f"FAIL: {error}", file=sys.stderr)
            failures += 1
        else:
            print(f"PASS: {pdf} ({PAGE_COUNTS[template]} pages, text and order match)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
