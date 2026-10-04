"""Setup diagnostics for missing, broken, and partial installations."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_setup as checker


class SetupTests(unittest.TestCase):
    def run_check(self, args=(), missing=(), failure=None):
        out = StringIO()
        def find(name):
            return None if name in missing else f"/test tools/{name}"
        def run(command, **kwargs):
            if failure:
                result = failure(command)
                if result is not None:
                    return result
            return subprocess.CompletedProcess(command, 0, stdout=b"available\n")
        with patch.object(checker.shutil, "which", side_effect=find), \
                patch.object(checker.subprocess, "run", side_effect=run) as process, \
                redirect_stdout(out):
            code = checker.main(list(args))
        return code, out.getvalue(), process

    def test_complete_installation_checks_tools_packages_and_fonts(self):
        code, out, process = self.run_check(["--pdf-checks"])
        self.assertEqual(code, 0)
        self.assertIn("Run make to check compilation", out)
        commands = [call.args[0] for call in process.call_args_list]
        self.assertIn(["/test tools/xelatex", "--version"], commands)
        self.assertIn(["/test tools/kpsewhich", "-progname=xelatex", "fontspec.sty"], commands)
        self.assertIn(["/test tools/kpsewhich", "-progname=xelatex", "lmroman10-bolditalic.otf"], commands)
        for call in process.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 10)
            self.assertNotIn("shell", call.kwargs)

    def test_missing_compiler_has_install_instructions(self):
        code, out, process = self.run_check(missing={"xelatex"})
        self.assertEqual(code, 1)
        self.assertIn("MISSING: xelatex", out)
        self.assertIn("PATH", out)
        self.assertIn("docs/local-setup.md", out)
        self.assertNotIn("Dependencies found", out)

    def test_missing_kpsewhich_does_not_claim_packages_are_present(self):
        code, out, process = self.run_check(missing={"kpsewhich"})
        self.assertEqual(code, 1)
        self.assertIn("SKIPPED: package and font checks", out)
        self.assertNotIn("OK: fontspec.sty", out)
        self.assertFalse(any("-progname=xelatex" in call.args[0] for call in process.call_args_list))

    def test_partial_installation_names_missing_font(self):
        def failure(command):
            if command[-1] == "lmroman10-regular.otf":
                return subprocess.CompletedProcess(command, 1)
        code, out, _ = self.run_check(failure=failure)
        self.assertEqual(code, 1)
        self.assertIn("MISSING: lmroman10-regular.otf", out)
        self.assertIn("package manager", out)

    def test_poppler_is_optional_until_pdf_checks_are_requested(self):
        for args, expected in (([], 0), (["--pdf-checks"], 1)):
            with self.subTest(args=args):
                code, out, _ = self.run_check(args, missing={"pdftotext", "pdfinfo"})
                self.assertEqual(code, expected)
                self.assertIn("Install Poppler", out)

    def test_broken_or_timed_out_tool_does_not_print_internal_errors(self):
        for error in (OSError("PRIVATE_SENTINEL"), subprocess.TimeoutExpired("PRIVATE_SENTINEL", 10)):
            def failure(command):
                if command[0].endswith("/latexmk"):
                    raise error
            with self.subTest(error=type(error).__name__):
                code, out, _ = self.run_check(failure=failure)
                self.assertEqual(code, 1)
                self.assertIn("latexmk was found but could not run", out)
                self.assertNotIn("PRIVATE_SENTINEL", out)


if __name__ == "__main__":
    unittest.main()
