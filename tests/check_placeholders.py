#!/usr/bin/env python3
"""Compile small resumes to verify automatic placeholder reminders."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import check_pdf_text


ROOT = Path(__file__).resolve().parents[1]
WARNING = "Class resume Warning: Placeholder reminder in "


def reminders(log):
    return [line.split(WARNING, 1)[1].strip() for line in log.splitlines() if WARNING in line]


def document(body, preamble=""):
    return "\\documentclass{resume}\n" + preamble + "\n\\begin{document}\n" + body + "\n\\end{document}\n"


class PlaceholderBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="resume-placeholders-")
        self.root = Path(self.temporary.name)
        self.count = 0

    def tearDown(self):
        self.temporary.cleanup()

    def compile(self, body, preamble=""):
        self.count += 1
        project = self.root / f"fixture {self.count}"
        project.mkdir()
        shutil.copyfile(ROOT / "resume.cls", project / "resume.cls")
        (project / "resume.tex").write_text(document(body, preamble), encoding="utf-8")
        result = subprocess.run(
            [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"],
            cwd=project,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, "\n".join(result.stdout.splitlines()[-35:]))
        log = (project / "resume.log").read_text(encoding="utf-8", errors="replace")
        for diagnostic in ("Invalid end-point", "Invalid regular expression", "Unknown special group", "Missing right bracket"):
            self.assertNotIn(diagnostic, log)
        text = check_pdf_text.extract_text(project / "resume.pdf")
        return reminders(log), text, log

    def test_sample_name_contact_and_entry_values_warn(self):
        warnings, _, log = self.compile(r"""
\resumename{Your Name}
\resumecontact{City, Region \contactsep \resumelink{tel:+15555555555}{Call}
\contactsep \resumelink{mailto:hello@example.com}{Email}
\contactsep \resumelink{https://github.com/your-handle}{GitHub}}
\jobentry{Issuing Organization}{Certification Name}{City, Region}{Year}
""")
        self.assertEqual(len(warnings), 6)
        for location in ("resume name", "contact details", "entry 1 role", "entry 1 organization", "entry 1 location", "entry 1 dates"):
            self.assertTrue(any(location in warning for warning in warnings), warnings)
        self.assertIn("on input line", log)

    def test_hidden_sample_profile_and_phone_urls_warn(self):
        warnings, _, _ = self.compile(r"""
\resumename{Alex Morgan}
\resumecontact{\resumelink{https://www.linkedin.com/in/your-handle}{Profile}}
\resumecontact{\resumelink{tel:+15555555555}{Call}}
\resumecontact{\resumelink{mailto:hello@example.com}{Email}}
""")
        self.assertEqual(warnings, ["contact details."] * 3)

    def test_bracketed_contacts_after_separator_warn(self):
        warnings, _, _ = self.compile(r"""
\resumename{Alex Morgan}
\resumecontact{Toronto, ON \contactsep [Phone]}
\resumecontact{Toronto, ON \contactsep []}
""")
        self.assertEqual(warnings, ["contact details."] * 2)

    def test_brackets_in_multiple_lists_and_summary_warn(self):
        warnings, _, log = self.compile(r"""
\resumename{Alex Morgan}
\jobentry[{Supports [N] teams}]{Engineer}{Acme}{Toronto}{2022 -- Present}
\begin{jobduties}
\item Built [private sentinel] with tests.
\end{jobduties}
\jobentry{Engineer}{Beta}{Toronto}{2020 -- 2022}
\begin{jobduties}
\item Fixed [failure].
\end{jobduties}
\begin{skillitems}
\item Python, [Language].
\end{skillitems}
""")
        self.assertEqual(warnings, ["entry 1 summary.", "entry 1 bullets.", "entry 2 bullets.", "skills bullets."])
        self.assertNotIn("private sentinel", log)

    def test_filled_content_comments_and_optional_syntax_do_not_warn(self):
        warnings, _, _ = self.compile(r"""
% Your Name [private prompt]
\resumename{Alex Morgan}
\resumecontact{Toronto, ON \contactsep \resumelink{mailto:alex@domain.test}{Email}}
\jobentry[Owns the billing service]{Engineer}{Acme Analytics}{Toronto}{2022 -- Present}
\begin{jobduties}
% \item Built [thing].
\item[--] Built a retry worker and tested duplicate delivery.
\item Reduced query time by \textcolor[rgb]{0,0,0}{20 percent}.
\end{jobduties}
\begin{skillitems}
\item Python, SQL, Linux.
\end{skillitems}
""")
        self.assertEqual(warnings, [])

    def test_legitimate_words_are_not_matched_as_sample_fields(self):
        warnings, _, _ = self.compile(r"""
\resumename{Your Namesake}
\resumecontact{Quebec City, QC}
\jobentry{Engineer}{Company Analytics}{Region City}{2024}
\begin{jobduties}
\item Added a Month Year selector and a Year filter.
\end{jobduties}
""")
        self.assertEqual(warnings, [])

    def test_empty_prompts_warn_but_command_options_do_not(self):
        warnings, _, _ = self.compile(r"""
\resumename{[]}
\jobentry[]{Engineer}{Acme}{Toronto}{2024}
\begin{jobduties}
\item[] \fixturecommand*[optional label]{Built a tested worker.}
\item \fixturetwo[first][second]{Shipped a retry fix.}\\[3pt]
Verified duplicate delivery.
\end{jobduties}
\begin{skillitems}
\item Python, [].
\end{skillitems}
""", r"""
\NewDocumentCommand{\fixturecommand}{s O{} m}{#3}
\NewDocumentCommand{\fixturetwo}{O{} O{} m}{#3}
""")
        self.assertEqual(warnings, ["resume name.", "skills bullets."])

    def test_subentry_and_letter_prompts_warn(self):
        warnings, text, _ = self.compile(r"""
\resumename{Alex Morgan}
\jobentry{}{Acme}{Toronto}{2020 -- Present}
\jobsubentry{[Current role]}{2023 -- Present}
\begin{jobduties}
\item Led the billing migration.
\end{jobduties}
\jobsubentry{Engineer}{Month Year -- 2023}
\begin{jobduties}
\item Built the retry worker.
\end{jobduties}
\letteropening{[Month Day, Year]}{Sam Lee}{}{Dear Sam,}
\begin{letterbody}
I am applying for [Role].

Second paragraph.
\end{letterbody}
\letterclosing{Sincerely,}{Your Name}
""")
        self.assertEqual(warnings, ["entry 2 role.", "entry 3 dates.", "letter date.", "letter body.", "letter signature."])
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        self.assertEqual(lines[1].split()[:2], ["Acme", "–"])
        self.assertTrue(lines[2].startswith("[Current role]"), lines[2])
        self.assertIn("Dear Sam,", lines)

    def test_rows_summary_letterfor_and_linked_titles_warn(self):
        warnings, text, _ = self.compile(r"""
\resumename{Alex Morgan}
\resumecontact{Toronto, ON}
\resumesummary{Backend engineer; [one more sentence].}
\jobentry{Personal project; Python}{\resumelink{https://github.com/your-handle/tool}{Import Tool}}{}{2025}
\resumerow{[Certification, Level]}{Issuing Organization}{2024}
\resumerow{AWS Certified Developer, Associate}{Amazon Web Services}{Month Year}
\letterfor{[Company]}{Backend Engineer}
\begin{letterbody}
I am applying for the \Role position at \Company. \Company's team ships weekly.
\end{letterbody}
""")
        self.assertEqual(warnings, [
            "summary.", "entry 1 organization.", "entry 2 name.", "entry 2 detail.",
            "entry 3 dates.", "letter company.",
        ])
        self.assertIn("Backend engineer; [one more sentence].", text)
        self.assertIn("Import Tool", text)
        self.assertIn("AWS Certified Developer, Associate – Amazon Web Services", text)
        self.assertIn("the Backend Engineer position at [Company]. [Company]\u2019s team", text)

    def test_empty_bullet_list_warns_instead_of_stopping(self):
        _, text, log = self.compile(r"""
\resumename{Alex Morgan}
\jobentry{Engineer}{Acme}{Toronto}{2024}
\begin{jobduties}
\end{jobduties}
""")
        self.assertIn("Empty jobduties list in entry 1", log)
        self.assertIn("Engineer", text)

    def test_letter_signature_uses_the_header_name_unless_overridden(self):
        for signature, expected in (("", "Alex Morgan"), ("Alex M.", "Alex M.")):
            with self.subTest(signature=signature):
                warnings, text, log = self.compile(
                    r"\resumename{Alex Morgan}\letterclosing{Sincerely,}{" + signature + "}"
                )
                self.assertEqual(warnings, [])
                self.assertNotIn("Missing letter signature", log)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                self.assertEqual(lines, ["Alex Morgan", "Sincerely,", expected])

    def test_letter_signature_requires_a_name_and_keeps_placeholder_reminders(self):
        warnings, text, log = self.compile(r"\letterclosing{Sincerely,}{}")
        self.assertEqual(warnings, [])
        self.assertIn("Missing letter signature name", log)
        self.assertIn(r"Set \resumename or give a name to \letterclosing", log)
        self.assertEqual(text.strip(), "Sincerely,")
        warnings, text, _ = self.compile(r"\resumename{Your Name}\letterclosing{Sincerely,}{}")
        self.assertEqual(warnings, ["resume name."])
        self.assertEqual(text.count("Your Name"), 2)

    def test_warning_checks_do_not_change_extracted_content(self):
        body = r"""
\resumename{Your Name}
\resumecontact{City, Region}
\jobentry[{Supports [N] teams}]{Engineer}{Company A}{City, Region}{Month Year -- Present}
\begin{jobduties}
\item Built [API] and tested [failure paths].
\end{jobduties}
\begin{skillitems}
\item Python, [Language].
\end{skillitems}
"""
        warnings, actual, _ = self.compile(body)
        silent, expected, _ = self.compile(body, r"\renewcommand{\resumecheckfield}[3]{}")
        self.assertTrue(warnings)
        self.assertEqual(silent, [])
        self.assertEqual(actual, expected)


def main():
    missing = [name for name in ("xelatex", "pdftotext") if shutil.which(name) is None]
    if missing:
        print(
            "FAIL: missing " + ", ".join(missing) + ". Install XeLaTeX and Poppler and add them to PATH.",
            file=sys.stderr,
        )
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlaceholderBuildTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
