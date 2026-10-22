#!/usr/bin/env python3
"""Build the optional application versions and test shared edits and selection."""

import argparse
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import check_contacts
import check_pdf_text
import check_placeholders


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT
DOWNLOADS_DIR = ROOT / "downloads"
VARIANTS = ("resume", "backend")
CONTACT_URLS = [
    "tel:+15555555555", "mailto:hello@example.com",
    "https://www.linkedin.com/in/your-handle", "https://github.com/your-handle",
]
ARCHIVE_FILES = frozenset({
    "resume.tex", "backend.tex", "setup.tex",
    "latexmkrc", "README.md", "resume.cls", "LICENSE",
    "content/profile.tex", "content/experience.tex", "content/education.tex",
    "content/skills.tex", "content/projects.tex",
})
SELECTIONS = {
    "resume": (
        "ToolWorkflow", "ToolRecovery", "ToolStorage",
        "CourseContribution", "CourseQueries", "CourseChecks",
    ),
    "backend": (
        "CourseContribution", "CourseQueries", "CourseChecks",
        "ToolWorkflow", "ToolStorage",
    ),
}
BULLET_STARTS = {
    "ToolWorkflow": "Built [application] so [users] could [task]",
    "ToolRecovery": "Preserved [user input] after failed requests",
    "ToolStorage": "Stored [records] in [database]",
    "CourseContribution": "Owned [component] in a [N]-person course project",
    "CourseQueries": "Changed [query or index] to handle [workload]",
    "CourseChecks": "Tested [operation] with [boundary condition]",
    "RoleFeature": "Built [feature] for [team or users]",
    "RoleFix": "Fixed [failure] in [workflow]",
}


class ApplicationError(Exception):
    """A project cannot be safely unpacked, compiled, or checked."""


def read_source(root):
    files = {}
    for name in sorted(ARCHIVE_FILES):
        source = root / name if name in {"resume.cls", "LICENSE"} else root / "examples/application-versions" / name
        if source.is_symlink() or not source.is_file():
            raise ApplicationError(f"Expected a regular source file: {source}")
        files[name] = source.read_text(encoding="utf-8").encode("utf-8")
    return files


def read_archive(path):
    """Validate the entire archive before extracting any of its files."""
    try:
        if path.is_symlink():
            raise ApplicationError(f"Refusing a symlink archive: {path}")
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise ApplicationError(f"{path}: duplicate ZIP entries")
            if set(names) != ARCHIVE_FILES:
                raise ApplicationError(f"{path}: unexpected ZIP contents; run make downloads")
            for entry in entries:
                mode = entry.external_attr >> 16
                if entry.is_dir() or entry.external_attr & 0x10 or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise ApplicationError(f"{path}: not a regular file: {entry.filename}")
                if entry.orig_filename != entry.filename:
                    raise ApplicationError(f"{path}: invalid ZIP filename")
            return {entry.filename: archive.read(entry) for entry in entries}
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise ApplicationError(f"Cannot read {path}: {error}. Run make downloads first.") from error


def write_project(files, project):
    if set(files) != ARCHIVE_FILES:
        raise ApplicationError("Unexpected project files; no files were written")
    project.mkdir()
    for name, content in files.items():
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def replace_once(files, name, before, after):
    """Fail loudly if a fixture no longer matches the example it is testing."""
    text = files[name].decode("utf-8")
    if text.count(before) != 1:
        raise ApplicationError(f"Expected exactly one fixture replacement in {name}: {before!r}")
    files[name] = text.replace(before, after).encode("utf-8")


def compile_project(project, variant, expect_failure=False):
    try:
        result = subprocess.run(
            [shutil.which("latexmk"), "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"{variant}.tex"],
            cwd=project, capture_output=True, encoding="utf-8", errors="replace", timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ApplicationError(f"Cannot compile {variant}: {error}") from error
    log_path = project / f"{variant}.log"
    log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else result.stdout + result.stderr
    if expect_failure:
        if result.returncode == 0:
            raise ApplicationError(f"{variant}: invalid command compiled without an error")
        return log
    if result.returncode:
        excerpt = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-40:])
        raise ApplicationError(f"{variant}: latexmk failed; check XeLaTeX and latexmkrc.\n{excerpt}")
    if "Overfull " in log:
        raise ApplicationError(f"{variant}: overfull text in the compiled example")
    return project / f"{variant}.pdf", check_pdf_text.extract_text(project / f"{variant}.pdf"), log


def check_selection(text, selected):
    flat = " ".join(check_pdf_text.words(text))
    positions = []
    for name, phrase in BULLET_STARTS.items():
        count = flat.count(phrase)
        expected = 1 if name in selected else 0
        if count != expected:
            raise ApplicationError(f"{name}: expected {expected} occurrence, got {count}")
    for name in selected:
        positions.append(flat.index(BULLET_STARTS[name]))
    if positions != sorted(positions):
        raise ApplicationError("Selected bullets do not follow the entry-file order")


def check_bounds(pdf, paper="letterpaper"):
    result = subprocess.run(
        [shutil.which("pdftotext"), "-bbox", str(pdf), "-"],
        check=True, capture_output=True, encoding="utf-8", timeout=30,
    )
    tree = ET.fromstring(result.stdout)
    pages = tree.findall(".//{*}page")
    if len(pages) != 1:
        raise ApplicationError(f"{pdf}: expected one page, got {len(pages)}")
    width, height = {"letterpaper": (612, 792), "a4paper": (595.276, 841.89)}[paper]
    if abs(float(pages[0].attrib["width"]) - width) > 0.1 or abs(float(pages[0].attrib["height"]) - height) > 0.1:
        raise ApplicationError(f"{pdf}: incorrect paper size for {paper}")
    words = pages[0].findall(".//{*}word")
    if not words:
        raise ApplicationError(f"{pdf}: no text boxes")
    boxes = []
    for word in words:
        x_min, y_min, x_max, y_max = (float(word.attrib[key]) for key in ("xMin", "yMin", "xMax", "yMax"))
        # The existing large name font's glyph box starts about 3.6 pt above
        # the 36 pt text margin. Keep that design; body text stays inside it.
        top = 31.5 if y_max - y_min > 25 and y_max < 65 else 35.5
        if x_min < 35.5 or x_max > width - 35.5 or y_min < top or y_max > height - 35.5:
            raise ApplicationError(f"{pdf}: text outside margins: {word.text}")
        boxes.append((x_min, y_min, x_max, y_max, word.text))
    for index, first in enumerate(boxes):
        for second in boxes[index + 1:]:
            x_overlap = min(first[2], second[2]) - max(first[0], second[0])
            y_overlap = min(first[3], second[3]) - max(first[1], second[1])
            if x_overlap > 0.5 and y_overlap > 0.5:
                raise ApplicationError(f"{pdf}: overlapping text: {first[4]}, {second[4]}")


def check_snapshot(pdf, variant, text=None):
    baseline = ROOT / "tests/expected" / f"application-{variant}-1.txt"
    try:
        expected = baseline.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ApplicationError(f"Cannot read reviewed baseline {baseline}: {error}") from error
    check_pdf_text.compare_pages(str(pdf), check_pdf_text.extract_text(pdf) if text is None else text, [expected])


class ApplicationVersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="application-versions-")
        self.root = Path(self.temporary.name)
        self.files = read_source(SOURCE_ROOT)

    def tearDown(self):
        self.temporary.cleanup()

    def project(self, name="source project"):
        path = self.root / name
        write_project(self.files, path)
        return path

    def guide_block(self, starts_with):
        blocks = re.findall(r"```latex\n(.*?)```", self.files["README.md"].decode("utf-8"), re.DOTALL)
        matching = [block for block in blocks if block.startswith(starts_with)]
        self.assertEqual(len(matching), 1, f"Expected one guide example beginning with {starts_with}")
        return matching[0]

    def test_source_and_exact_download_build_all_versions(self):
        downloaded = read_archive(DOWNLOADS_DIR / "application-versions.zip")
        self.assertEqual(downloaded, self.files, "The ZIP does not match the current source; run make downloads")
        for kind, files in (("source", self.files), ("download", downloaded)):
            checkout = self.root / f"{kind} project with spaces"
            project = checkout / "examples/application-versions" if kind == "source" else checkout
            project.parent.mkdir(parents=True, exist_ok=True)
            write_project(files, project)
            if kind == "source":
                # Match a checkout: the shared class is two directories up.
                # This exercises latexmkrc, not a test-only TEXINPUTS override.
                (project / "resume.cls").rename(checkout / "resume.cls")
                (project / "LICENSE").rename(checkout / "LICENSE")
                self.assertFalse((project / "resume.cls").exists())
            for variant in VARIANTS:
                with self.subTest(kind=kind, variant=variant):
                    pdf, text, log = compile_project(project, variant)
                    check_snapshot(pdf, variant, text)
                    check_selection(text, SELECTIONS[variant])
                    check_bounds(pdf)
                    self.assertEqual(check_contacts.extract_urls(pdf), CONTACT_URLS)
                    self.assertEqual(check_placeholders.reminders(log).count("selected bullet."), len(SELECTIONS[variant]))
                    self.assertNotIn("Experience", text)
                    self.assertNotIn("[Employer]", text)

    def test_all_versions_fit_a4_without_overlap(self):
        for variant in VARIANTS:
            replace_once(self.files, f"{variant}.tex", r"\documentclass{resume}", r"\documentclass[a4paper]{resume}")
        project = self.project()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                pdf, text, _ = compile_project(project, variant)
                check_selection(text, SELECTIONS[variant])
                check_bounds(pdf, "a4paper")

    def test_shared_contact_education_and_project_edits_reach_every_version(self):
        for before, after in (
            ("Your Name", "Alex Morgan"), ("hello@example.com", "alex_morgan+jobs@domain.test"),
            ("+1 (555) 555-5555", "+44 (20) 5555-0123"),
        ):
            replace_once(self.files, "content/profile.tex", before, after)
        replace_once(self.files, "content/education.tex", "[University]", "Example Institute")
        replace_once(self.files, "content/education.tex", "[Graduation Month Year]", "May 2021")
        replace_once(self.files, "content/projects.tex", "[Personal project]", "Reading List")
        replace_once(self.files, "content/projects.tex", "[Course project]", "Course Scheduler")
        project = self.project()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                pdf, text, _ = compile_project(project, variant)
                flat = " ".join(check_pdf_text.words(text))
                for phrase in ("Alex Morgan", "alex_morgan+jobs@domain.test", "+44 (20) 5555-0123", "Example Institute", "May 2021", "Reading List", "Course Scheduler"):
                    self.assertIn(phrase, flat)
                self.assertNotIn("Your Name", text)
                self.assertNotIn("hello@example.com", text)
                self.assertIn("mailto:alex_morgan+jobs@domain.test", check_contacts.extract_urls(pdf))
                self.assertIn("tel:+442055550123", check_contacts.extract_urls(pdf))
                check_bounds(pdf)

    def test_optional_work_uses_shared_role_facts_and_selected_bullets(self):
        for variant in VARIANTS:
            name = f"{variant}.tex"
            source = self.files[name].decode("utf-8")
            start = source.index("% BEGIN OPTIONAL EXPERIENCE\n") + len("% BEGIN OPTIONAL EXPERIENCE\n")
            stop = source.index("% END OPTIONAL EXPERIENCE", start)
            commented = source[start:stop]
            self.assertTrue(all(line.startswith("% ") for line in commented.splitlines()))
            replace_once(self.files, name, commented, "".join(line[2:] for line in commented.splitlines(keepends=True)))
        for before, after in (
            ("[Actual role]", "Software Engineering Intern"),
            ("[Employer]", "Example Cooperative"),
            ("[City, Region]", "Toronto, Ontario"),
            ("[Month Year] -- [Month Year]", "May 2025 -- August 2025"),
        ):
            replace_once(self.files, "content/experience.tex", before, after)
        project = self.project()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                pdf, text, log = compile_project(project, variant)
                flat = " ".join(check_pdf_text.words(text))
                for phrase in ("Experience", "Software Engineering Intern", "Example Cooperative", "Toronto, Ontario", "May 2025 – August 2025"):
                    self.assertIn(phrase, flat)
                selection = (*SELECTIONS[variant], "RoleFeature", "RoleFix")
                check_selection(text, selection)
                self.assertEqual(check_placeholders.reminders(log).count("selected bullet."), len(selection))
                check_bounds(pdf)

    def test_bullet_edits_reach_only_versions_selecting_them(self):
        replace_once(self.files, "content/projects.tex", "Built [application] so [users] could [task]", "Built a shared reading list")
        replace_once(self.files, "content/projects.tex", "Preserved [user input] after failed requests", "Preserved a reading-list draft after failed requests")
        project = self.project()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                _, text, _ = compile_project(project, variant)
                flat = " ".join(check_pdf_text.words(text))
                self.assertEqual(flat.count("Built a shared reading list"), 1)
                self.assertEqual(flat.count("Preserved a reading-list draft"), int(variant == "resume"))
                self.assertNotIn("Built [application]", flat)

    def test_named_application_can_reorder_and_drop_bullets_independently(self):
        project = self.project()
        named = project / "company-backend.tex"
        shutil.copyfile(project / "resume.tex", named)
        source = named.read_text(encoding="utf-8")
        original = "\\SharedToolProject\n\\begin{jobduties}\n  \\ToolWorkflow\n  \\ToolRecovery\n  \\ToolStorage\n\\end{jobduties}\n"
        self.assertEqual(source.count(original), 1)
        named.write_text(source.replace(original, self.guide_block(r"\SharedToolProject")), encoding="utf-8")
        pdf, text, _ = compile_project(project, "company-backend")
        check_selection(text, ("ToolStorage", "ToolWorkflow", "CourseContribution", "CourseQueries", "CourseChecks"))
        check_bounds(pdf)
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                _, text, _ = compile_project(project, variant)
                check_selection(text, SELECTIONS[variant])

    def test_migration_guide_compiles_existing_project_text_in_both_versions(self):
        definitions = self.guide_block(r"\newcommand{\SharedMyProject}")
        for before, after in (
            ("[Project type and tools]", "Personal project; Python, SQLite"),
            ("[Project name]", "Reading Notes"),
            ("[Dates]", "September 2025"),
            ("[Your existing bullet text]", "Saved notes in SQLite and tested persistence after restarting the app."),
        ):
            self.assertEqual(definitions.count(before), 1)
            definitions = definitions.replace(before, after)
        self.files["content/projects.tex"] += definitions.encode("utf-8")
        selected = self.guide_block(r"\SharedMyProject")
        for variant in VARIANTS:
            name = f"{variant}.tex"
            source = self.files[name].decode("utf-8")
            start = source.index("\\section{Projects}\n") + len("\\section{Projects}\n")
            stop = source.index("% BEGIN OPTIONAL EXPERIENCE", start)
            replace_once(self.files, name, source[start:stop], selected + "\n")
        project = self.project()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                pdf, text, log = compile_project(project, variant)
                flat = " ".join(check_pdf_text.words(text))
                for phrase in ("Reading Notes", "Personal project; Python, SQLite", "September 2025", "Saved notes in SQLite and tested persistence after restarting the app."):
                    self.assertIn(phrase, flat)
                check_selection(text, ())
                self.assertNotIn("selected bullet.", check_placeholders.reminders(log))
                self.assertNotIn("Experience", text)
                check_bounds(pdf)

    def test_misspelled_bullet_stops_compilation(self):
        replace_once(self.files, "backend.tex", r"\ToolWorkflow", r"\ToolTypoSentinel")
        log = compile_project(self.project(), "backend", expect_failure=True)
        self.assertIn("Undefined control sequence", log)
        self.assertIn("ToolTypoSentinel", log)

    def test_only_selected_bullets_emit_placeholder_reminders(self):
        self.files["backend.tex"] = (
            r"\documentclass{resume}\input{setup}\begin{document}"
            r"\begin{jobduties}\ToolWorkflow\end{jobduties}\end{document}"
        ).encode("utf-8")
        _, text, log = compile_project(self.project("selected prompt"), "backend")
        self.assertEqual(check_placeholders.reminders(log), ["selected bullet."])
        self.assertIn("[application]", text)
        replace_once(self.files, "content/projects.tex",
                     "Built [application] so [users] could [task].",
                     "Built a reading list so classmates could share course references.")
        _, text, log = compile_project(self.project("unused prompts"), "backend")
        self.assertEqual(check_placeholders.reminders(log), [])
        self.assertNotIn("[", text)
        self.assertNotIn("[operation]", text)


def check_published(pdf_dir):
    for variant in VARIANTS:
        pdf = pdf_dir / f"application-{variant}.pdf"
        text = check_pdf_text.extract_text(pdf)
        check_snapshot(pdf, variant, text)
        check_selection(text, SELECTIONS[variant])
        check_bounds(pdf)
        if check_contacts.extract_urls(pdf) != CONTACT_URLS:
            raise ApplicationError(f"{pdf}: contact destinations changed")
        print(f"PASS: {pdf} (one page, selected text and layout match)")


def main(argv=None):
    global SOURCE_ROOT, DOWNLOADS_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", action="store_true", help="check only the published PDFs")
    parser.add_argument("--pdf-dir", type=Path, default=ROOT / "output/pdf")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--downloads-dir", type=Path, default=ROOT / "downloads")
    args = parser.parse_args(argv)
    dependencies = ("pdftotext", "pdfinfo") if args.published else ("latexmk", "xelatex", "pdftotext", "pdfinfo")
    missing = [name for name in dependencies if shutil.which(name) is None]
    if missing:
        print("FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX, latexmk, and Poppler.", file=sys.stderr)
        return 1
    if args.published:
        try:
            check_published(args.pdf_dir)
        except (ApplicationError, check_pdf_text.CheckError, AssertionError, OSError, RuntimeError, subprocess.SubprocessError, ET.ParseError) as error:
            print(f"FAIL: {error}", file=sys.stderr)
            return 1
        return 0
    SOURCE_ROOT, DOWNLOADS_DIR = args.source_root, args.downloads_dir
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ApplicationVersionTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
