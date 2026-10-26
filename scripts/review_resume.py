#!/usr/bin/env python3
"""Build one chosen resume and summarize its reminders and PDF text checks."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

import check_resume


ROOT = Path(__file__).resolve().parents[1]
BUILD_TIMEOUT = 180
PLACEHOLDER = "Class resume Warning: Placeholder reminder in "
PAGE_EXCEEDED = "Class resume Warning: Page limit exceeded:"
PAGE_INVALID = "Class resume Warning: Invalid page limit."
CONTACT_UNSUPPORTED = "Class resume Warning: Unsupported "


def run_build(command, *, cwd, stdout, timeout):
    """Stop the compiler as well as latexmk when the build times out."""
    with subprocess.Popen(
        command, cwd=cwd, stdout=stdout, stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    ) as process:
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=10, check=True,
                        )
                    except (OSError, subprocess.SubprocessError) as error:
                        raise OSError("Could not stop compiler subprocesses. End them in Task Manager.") from error
            finally:
                process.kill()
                process.wait()
            raise


def summarize_warnings(log):
    """Report known compiler warnings without quoting or expanding resume content."""
    reminders = False
    lines = log.splitlines()
    placeholders = [number for number, line in enumerate(lines, 1) if PLACEHOLDER in line]
    if placeholders:
        reminders = True
        print(f"PLACEHOLDERS: {len(placeholders)} reminder(s); first at LaTeX log line {placeholders[0]}.")
        print("Replace sample values and prompts, or delete unused entries, then rebuild.")
        print("For shared content, follow the log into content/*.tex; literal brackets can also warn.")
    else:
        print("Placeholders: no class reminders found. Unmarked examples and custom commands can be missed.")

    contacts = [
        number for number, line in enumerate(lines, 1)
        if CONTACT_UNSUPPORTED in line and "format; contact is not linked." in line
    ]
    if contacts:
        reminders = True
        print(f"CONTACT LINKS: {len(contacts)} unsupported format(s); first at LaTeX log line {contacts[0]}.")
        print("The contact text is printed without a link. Correct the email or include the phone country code.")
        print(r"For other contact formats, use \resumelink{destination}{label}; check the exported PDF's links.")

    overflows = [
        number for number, line in enumerate(lines, 1)
        if line.lstrip().startswith((r"Overfull \hbox", r"Overfull \vbox"))
    ]
    if overflows:
        reminders = True
        print(f"LAYOUT OVERFLOW: {len(overflows)} box warning(s); first at LaTeX log line {overflows[0]}.")
        print("Inspect the PDF for clipped or overflowing text. Shorten long text or adjust the affected entry, then rebuild.")

    page_warnings = [
        (number, line.strip()) for number, line in enumerate(lines, 1)
        if PAGE_EXCEEDED in line or PAGE_INVALID in line
    ]
    for number, line in page_warnings:
        reminders = True
        print(f"PAGE WARNING (LaTeX log line {number}): {line}")
        if PAGE_INVALID in line:
            print(r"Use a whole number from 1 to 999999999 in \resumepagelimit{N}, then rebuild.")
        else:
            print(r"Cut less relevant content or change \resumepagelimit{N} if the extra page is intentional.")
    if not page_warnings:
        print("Source page reminders: none found; this does not establish that a source limit is enabled.")
    print("Other LaTeX warnings are not summarized. Read the logs for rerun, font, and other layout warnings.")
    return reminders


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Uses latexmk/XeLaTeX and Poppler locally. Each run gets a fresh folder "
            "in .context/final-review/ in this checkout. No published files are updated. "
            "Exit codes: 0 checks completed without reminders, 1 failed check, "
            "2 invalid arguments, 3 source reminders need review. "
            "This does not check layout, reading order, missing words, claims, or link destinations."
        ),
    )
    parser.add_argument("source", type=Path, help="exactly one LaTeX entry file (.tex); no default")
    parser.add_argument(
        "--max-pages", type=check_resume.positive_integer, metavar="N",
        help="check the extracted page count against N; no command limit by default",
    )
    args = parser.parse_args(argv)
    try:
        source = args.source.expanduser().resolve(strict=True)
        if not source.is_file() or source.suffix.lower() != ".tex":
            parser.error("Choose one .tex entry file, such as resume.tex or backend.tex.")
    except (OSError, RuntimeError, ValueError):
        parser.error("Cannot read the chosen source. Check its path and permissions.")

    print(f"Source: {source}")
    for tool, remedy in (
        ("latexmk", "Install latexmk from your TeX distribution and add it to PATH."),
        ("xelatex", "Install XeLaTeX from your TeX distribution and add it to PATH."),
        ("pdftotext", "Install Poppler and add its bin directory to PATH."),
    ):
        if shutil.which(tool) is None:
            print(f"FAIL: {tool} not found. {remedy}", file=sys.stderr)
            print("No build was started. See docs/local-setup.md for installation steps.", file=sys.stderr)
            return 1

    try:
        build_root = ROOT / ".context" / "final-review"
        # Do not follow a redirected output folder into published files.
        if build_root.resolve() != build_root:
            raise OSError("The review output directory must not be a symlink.")
        build_root.mkdir(parents=True, exist_ok=True)
        build_dir = Path(tempfile.mkdtemp(prefix="run-", dir=build_root))
        build_log = build_dir / "latexmk-output.txt"
        latex_log = build_dir / f"{source.stem}.log"
        pdf = build_dir / f"{source.stem}.pdf"
        print(f"Build log: {build_log}")
        print(f"LaTeX log (if created): {latex_log}")

        # Match the Makefile's root-relative templates and the standalone
        # projects' own latexmkrc / relative inputs. Never invoke an all target.
        project = ROOT if source.parent == ROOT / "templates" else source.parent
        with build_log.open("w", encoding="utf-8") as output:
            returncode = run_build(
                [
                    shutil.which("latexmk"), "-xelatex", "-g",
                    "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
                    f"-outdir={build_dir}", f"-auxdir={build_dir}",
                    "-e", "$out2_dir = '';", str(source),
                ],
                cwd=project, stdout=output, timeout=BUILD_TIMEOUT,
            )
        if returncode:
            print("FAIL: Compilation failed. Fix the first error in the build/LaTeX log and rerun.", file=sys.stderr)
            print("No PDF from this run is ready for review; do not use an older PDF.", file=sys.stderr)
            return 1
        if not pdf.is_file() or pdf.stat().st_size == 0:
            print("FAIL: Compilation did not produce the expected PDF in this run's folder.", file=sys.stderr)
            print("Check the build log and latexmk output settings, then rerun.", file=sys.stderr)
            return 1
        print(f"Built PDF: {pdf}")
        log = latex_log.read_text(encoding="utf-8", errors="replace")
        if not log.strip():
            raise OSError("The LaTeX log is empty.")
    except subprocess.TimeoutExpired:
        print(f"FAIL: Compilation exceeded {BUILD_TIMEOUT} seconds. Inspect the build log and resolve rerun loops or TeX errors.", file=sys.stderr)
        print("No PDF from this run is ready for review.", file=sys.stderr)
        return 1
    except (OSError, RuntimeError) as error:
        print(f"FAIL: Cannot build or read this run's files: {error}", file=sys.stderr)
        print("Check source/output permissions, latexmk settings, and the logs; warning checks are incomplete.", file=sys.stderr)
        return 1

    reminders = summarize_warnings(log)
    try:
        text = check_resume.extract_text(pdf)
        # Keep the page comparison separate so it cannot hide a text failure.
        pages = check_resume.check_text(text)
    except check_resume.CheckError as error:
        print(f"FAIL: PDF extraction check: {error}", file=sys.stderr)
        print("Open this PDF in the offline reviewer; compare its text with the source, fix fonts or text encoding, and rebuild.", file=sys.stderr)
        return 1
    print(f"Text checks: {pages} page(s); text on every page; no flagged characters.")
    if args.max_pages is not None:
        if pages > args.max_pages:
            print(f"FAIL: Page limit: found {pages} pages; --max-pages is {args.max_pages}.", file=sys.stderr)
            print("Cut less relevant content, or change --max-pages only if the application's instructions allow it.", file=sys.stderr)
            return 1
        print(f"Command page limit: {pages} of {args.max_pages} allowed.")
    else:
        print("Command page limit: not checked; pass --max-pages N to apply the application's limit.")
    print("Next: inspect the extracted text, every PDF page, and link destinations in the offline reviewer.")
    print("These checks do not verify layout, reading order, missing words, claims, or links. See docs/before-you-send.md.")
    if reminders:
        print("REVIEW NEEDED: source reminders remain; compilation and text extraction completed.")
        return 3
    print("Automated checks completed without source reminders; manual review is still needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
