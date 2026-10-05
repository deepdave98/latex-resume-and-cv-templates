#!/usr/bin/env python3
"""Check local tools and LaTeX dependencies without building a resume."""

import argparse
import shutil
import subprocess
import sys


TEX_FILES = (
    "article.cls", "geometry.sty", "xcolor.sty", "fontspec.sty", "titlesec.sty",
    "enumitem.sty", "etoolbox.sty", "needspace.sty", "ulem.sty", "hyperref.sty",
    "lmroman10-regular.otf", "lmroman10-bold.otf", "lmroman10-italic.otf",
    "lmroman10-bolditalic.otf",
)
TOOL_ARGUMENTS = {"xelatex": "--version", "latexmk": "-v", "kpsewhich": "--version"}


def runs(command):
    try:
        return subprocess.run(command, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-checks", action="store_true",
        help="also require Poppler's pdftotext and pdfinfo for make test",
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
        elif not runs([executable, argument]):
            print(f"ERROR: {name} was found but could not run. Check your TeX installation.")
            failures += 1
        else:
            available[name] = executable
            print(f"OK: {name}")

    if "kpsewhich" in available:
        for filename in TEX_FILES:
            if runs([available["kpsewhich"], "-progname=xelatex", filename]):
                print(f"OK: {filename}")
            else:
                print(f"MISSING: {filename}. Install it with your TeX distribution's package manager.")
                failures += 1
    else:
        print("SKIPPED: package and font checks need a working kpsewhich.")

    for name in ("pdftotext", "pdfinfo"):
        executable = shutil.which(name)
        if executable is not None and runs([executable, "-v"]):
            print(f"OK: {name}")
        elif args.pdf_checks:
            print(f"MISSING: working {name}. Install Poppler to run make test.")
            failures += 1
        else:
            print(f"OPTIONAL: {name} is unavailable. Install Poppler to run make test.")

    if failures:
        print("Install instructions: docs/local-setup.md")
        return 1
    print("Dependencies found. Run make to check compilation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
