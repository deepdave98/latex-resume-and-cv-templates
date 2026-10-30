"""Tests for the read-only local dependency check."""

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
    def run_check(self, args=(), *, missing=(), failure=None):
        output = StringIO()

        def run(command, **kwargs):
            if failure:
                result = failure(command)
                if result is not None:
                    return result
            return subprocess.CompletedProcess(command, 0, stdout=b"available\n")

        with patch.object(checker.shutil, "which", side_effect=lambda name: (
            None if name in missing else f"/test tools/{name}"
        )), patch.object(checker.subprocess, "run", side_effect=run) as commands:
            with redirect_stdout(output):
                code = checker.main(args)
        return code, output.getvalue(), commands.call_args_list

    def test_complete_install_checks_real_commands_and_groups_files(self):
        code, output, commands = self.run_check()
        self.assertEqual(code, 0)
        called = [call.args[0] for call in commands]
        for tool, argument in checker.TOOL_ARGUMENTS.items():
            self.assertIn([f"/test tools/{tool}", argument], called)
        for filename in checker.TEX_FILES:
            self.assertIn(["/test tools/kpsewhich", "-progname=xelatex", filename], called)
            self.assertNotIn(f"OK: {filename}", output)
        self.assertIn("OK: resume.cls packages and Latin Modern fonts", output)
        self.assertIn("Run make to check compilation", output)
        for call in commands:
            self.assertEqual(call.kwargs, {"capture_output": True, "timeout": 10})

    def test_missing_build_tool_has_path_guidance(self):
        code, output, _ = self.run_check(missing=("xelatex",))
        self.assertEqual(code, 1)
        self.assertIn("MISSING: xelatex", output)
        self.assertIn("bin directory to PATH", output)
        self.assertNotIn("Dependencies found", output)

    def test_missing_kpsewhich_skips_file_checks(self):
        code, output, commands = self.run_check(missing=("kpsewhich",))
        self.assertEqual(code, 1)
        self.assertIn("SKIPPED: package and font checks", output)
        self.assertNotIn("OK: resume.cls", output)
        self.assertFalse(any("-progname=xelatex" in call.args[0] for call in commands))

    def test_missing_font_and_empty_lookup_are_not_success(self):
        font = "lmroman10-bold.otf"
        for status, stdout, reason in ((1, b"", "not found"), (0, b" \n", "returned no path")):
            with self.subTest(status=status):
                code, output, _ = self.run_check(failure=lambda command: (
                    subprocess.CompletedProcess(command, status, stdout=stdout)
                    if command[-1] == font else None
                ))
                self.assertEqual(code, 1)
                self.assertIn(f"MISSING: {font} ({reason})", output)
                self.assertIn("package manager", output)
                self.assertNotIn("OK: resume.cls", output)

    def test_poppler_is_optional_unless_requested(self):
        for args, code, label in (((), 0, "OPTIONAL"), (("--pdf-checks",), 1, "ERROR")):
            with self.subTest(args=args):
                actual, output, _ = self.run_check(args, missing=("pdftotext", "pdfinfo"))
                self.assertEqual(actual, code)
                self.assertIn(f"{label}: pdftotext not found on PATH", output)
                self.assertIn(f"{label}: pdfinfo not found on PATH", output)

    def test_tool_failures_are_actionable_without_dumping_command_output(self):
        for failure, reason in (
            (OSError("PRIVATE_SENTINEL"), "could not start"),
            (subprocess.TimeoutExpired("PRIVATE_SENTINEL", 10), "timed out after 10 seconds"),
            (2, "exited with status 2"),
        ):
            with self.subTest(reason=reason):
                def fail(command):
                    if command[0].endswith("/latexmk"):
                        if isinstance(failure, Exception):
                            raise failure
                        return subprocess.CompletedProcess(command, failure, stdout=b"PRIVATE_SENTINEL")
                    return None

                code, output, _ = self.run_check(failure=fail)
                self.assertEqual(code, 1)
                self.assertIn(f"ERROR: latexmk {reason}", output)
                self.assertNotIn("PRIVATE_SENTINEL", output)

    def test_failed_lookup_is_reported_as_error(self):
        code, output, _ = self.run_check(failure=lambda command: (
            subprocess.CompletedProcess(command, 2, stdout=b"")
            if command[-1] == "article.cls" else None
        ))
        self.assertEqual(code, 1)
        self.assertIn("ERROR: article.cls (exited with status 2)", output)

    def test_old_python_is_reported(self):
        with patch.object(checker.sys, "version_info", (3, 8)):
            code, output, _ = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("MISSING: Python 3.9 or newer", output)


if __name__ == "__main__":
    unittest.main()
