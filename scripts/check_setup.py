#!/usr/bin/env python3
"""Check local build tools and resume.cls dependencies without compiling a resume."""

import argparse
import shutil
import subprocess
import sys


TEX_FILES = (
    "article.cls", "geometry.sty", "xcolor.sty", "fontspec.sty",
    "titlesec.sty", "enumitem.sty", "etoolbox.sty", "needspace.sty",
    "ulem.sty", "hyperref.sty", "lmroman10-regular.otf", "lmroman10-bold.otf",
    "lmroman10-italic.otf", "lmroman10-bolditalic.otf",
)
TOOL_ARGUMENTS = {"xelatex": "--version", "latexmk": "-v", "kpsewhich": "--version"}
TIMEOUT_SECONDS = 10


def command_problem(command, *, lookup=False):
    """Return a short failure reason, or None when the command succeeds."""
    try:
        result = subprocess.run(command, capture_output=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return f"timed out after {TIMEOUT_SECONDS} seconds"
    except OSError:
        return "could not start"
    if result.returncode:
        if lookup and result.returncode == 1:
            return "not found"
        return f"exited with status {result.returncode}"
    if lookup and not result.stdout.strip():
        return "returned no path"
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-checks", action="store_true",
        help="also require Poppler's pdftotext and pdfinfo for PDF checks",
    )
    args = parser.parse_args(argv)
    failures = 0
    if sys.version_info < (3, 9):
        print("MISSING: Python 3.9 or newer.")
        failures += 1
    else:
        print(f"OK: Python {sys.version_info.major}.{sys.version_info.minor}")

    available = {}
    for name, argument in TOOL_ARGUMENTS.items():
        executable = shutil.which(name)
        if executable is None:
            print(f"MISSING: {name}. Add your TeX installation's bin directory to PATH.")
            failures += 1
            continue
        problem = command_problem([executable, argument])
        if problem:
            print(f"ERROR: {name} {problem}. Check your TeX installation.")
            failures += 1
        else:
            available[name] = executable
            print(f"OK: {name}")

    if "kpsewhich" in available:
        missing_files = 0
        for filename in TEX_FILES:
            problem = command_problem(
                [available["kpsewhich"], "-progname=xelatex", filename], lookup=True,
            )
            if problem:
                label = "MISSING" if problem in ("not found", "returned no path") else "ERROR"
                print(f"{label}: {filename} ({problem}). Check your TeX distribution's package manager.")
                missing_files += 1
        failures += missing_files
        if not missing_files:
            print("OK: resume.cls packages and Latin Modern fonts")
    else:
        print("SKIPPED: package and font checks need a working kpsewhich.")

    for name in ("pdftotext", "pdfinfo"):
        executable = shutil.which(name)
        problem = command_problem([executable, "-v"]) if executable else "not found on PATH"
        if problem is None:
            print(f"OK: {name}")
        else:
            label = "ERROR" if args.pdf_checks else "OPTIONAL"
            print(f"{label}: {name} {problem}. Install or repair Poppler to run PDF checks.")
            failures += int(args.pdf_checks)

    if failures:
        print("Install instructions: docs/local-setup.md")
        return 1
    print("Dependencies found. Run make to check compilation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
