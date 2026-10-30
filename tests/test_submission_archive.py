"""Submission copies preserve the chosen bytes without collecting other files."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "scripts"))
import archive_resume as archive


class SubmissionArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="submission archive ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "my resume"
        self.project.mkdir()
        self.source = self.project / "chosen.pdf"
        self.content = b"%PDF-1.7\nPRIVATE_RESUME_CONTENT\n%%EOF\n"
        self.source.write_bytes(self.content)
        root = patch.object(archive, "ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)

    def run_main(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = archive.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def symlink(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks unavailable: {error}")

    def test_receipt_describes_exact_selected_bytes_and_collects_nothing_else(self):
        for name in ("resume.tex", "private-bank.tex", "other.pdf", ".env"):
            (self.project / name).write_bytes(b"UNSELECTED_PRIVATE_CONTENT")
        before = datetime.now(timezone.utc)
        saved = archive.archive_pdf(self.source, "Acme Backend")
        after = datetime.now(timezone.utc)
        receipt = json.loads((saved / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(set(receipt), {"label", "saved_at", "pdf", "bytes", "sha256"})
        timestamp = datetime.fromisoformat(receipt["saved_at"])
        self.assertIsNotNone(timestamp.utcoffset())
        self.assertLessEqual(before.replace(microsecond=0), timestamp)
        self.assertLessEqual(timestamp, after)
        self.assertEqual(saved.parent, self.root / "submissions")
        self.assertEqual(saved.name, f"{timestamp.date().isoformat()}-acme-backend")
        self.assertEqual(receipt["label"], "Acme Backend")
        self.assertEqual(receipt["pdf"], "resume-acme-backend.pdf")
        self.assertEqual(receipt["bytes"], len(self.content))
        self.assertIs(type(receipt["bytes"]), int)
        self.assertEqual(receipt["sha256"], hashlib.sha256(self.content).hexdigest())
        self.assertEqual({p.name for p in saved.iterdir()}, {"resume-acme-backend.pdf", "receipt.json"})
        self.assertEqual((saved / receipt["pdf"]).read_bytes(), self.content)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertNotIn(str(self.source), (saved / "receipt.json").read_text(encoding="utf-8"))
        self.source.write_bytes(b"%PDF-1.7\nLATER_RESUME_REVISION\n")
        self.assertEqual((saved / receipt["pdf"]).read_bytes(), self.content)

    def test_published_pdf_copies_without_changes_to_its_bytes(self):
        source = REPOSITORY / "output/pdf/new-grad-resume.pdf"
        original = source.read_bytes()
        saved = archive.archive_pdf(source, "Published sample")
        self.assertEqual((saved / "resume-published-sample.pdf").read_bytes(), original)
        self.assertEqual(source.read_bytes(), original)
        receipt = json.loads((saved / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["sha256"], hashlib.sha256(original).hexdigest())

    def test_labels_form_short_local_filenames_with_unicode_letters(self):
        for label, slug in (
            ("  Acme / Backend: Canada  ", "acme-backend-canada"),
            ("../../Acme\\Platform", "acme-platform"),
            ("Québec / 软件 42", "québec-软件-42"),
            ("İstanbul", "i-stanbul"),
            ("A" * 100, "a" * 80),
        ):
            with self.subTest(label=label):
                saved = archive.archive_pdf(self.source, label)
                self.assertEqual(saved.parent, self.root / "submissions")
                self.assertTrue((saved / f"resume-{slug}.pdf").is_file())
                self.assertTrue(all(char.isalnum() or char == "-" for char in slug))

    def test_device_name_labels_produce_portable_pdf_filenames(self):
        is_reserved = getattr(ntpath, "isreserved", lambda name: PureWindowsPath(name).is_reserved())
        for label in ("CON", "AUX", "COM1", "LPT9", "NUL"):
            with self.subTest(label=label):
                saved = archive.archive_pdf(self.source, label)
                receipt = json.loads((saved / "receipt.json").read_text(encoding="utf-8"))
                self.assertFalse(is_reserved(saved.name))
                self.assertFalse(is_reserved(receipt["pdf"]))
                self.assertEqual((saved / receipt["pdf"]).read_bytes(), self.content)

    def test_long_unicode_labels_fit_filesystem_filename_limits(self):
        saved = archive.archive_pdf(self.source, "\U00020000" * 100)
        receipt = json.loads((saved / "receipt.json").read_text(encoding="utf-8"))
        self.assertLessEqual(len(saved.name.encode("utf-8")), 255)
        self.assertLessEqual(len(receipt["pdf"].encode("utf-8")), 255)
        self.assertEqual((saved / receipt["pdf"]).read_bytes(), self.content)

    def test_empty_punctuation_and_control_labels_are_rejected(self):
        for label in ("", "   ", "../--", "\nAcme", "Acme\t", "Acme\nRole", "Acme\x00", "Acme\u200b"):
            with self.subTest(label=repr(label)), self.assertRaises(archive.ArchiveError):
                archive.archive_pdf(self.source, label)
        self.assertFalse((self.root / "submissions").exists())

    def test_non_pdf_missing_and_directory_inputs_create_no_archive(self):
        for content in (b"", b"PRIVATE_RESUME_CONTENT", b"%PDF-x.y\n", b"%PDF-1\n"):
            self.source.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(archive.ArchiveError):
                archive.archive_pdf(self.source, "Acme")
        for source in (self.project, self.root / "missing.pdf"):
            with self.subTest(source=source.name), self.assertRaises((archive.ArchiveError, OSError)):
                archive.archive_pdf(source, "Acme")
        self.assertFalse((self.root / "submissions").exists())

    def test_duplicate_label_and_slug_collision_preserve_existing_archive(self):
        saved = archive.archive_pdf(self.source, "Acme Backend")
        before = {path.name: path.read_bytes() for path in saved.iterdir()}
        self.source.write_bytes(b"%PDF-1.7\nREPLACEMENT_CONTENT\n")
        for label in ("Acme Backend", "Acme/Backend"):
            with self.subTest(label=label), self.assertRaises(archive.ArchiveError):
                archive.archive_pdf(self.source, label)
        self.assertEqual({path.name: path.read_bytes() for path in saved.iterdir()}, before)
        self.assertEqual(list(saved.parent.iterdir()), [saved])

    def test_existing_file_or_symlink_destination_is_not_replaced(self):
        saved = archive.archive_pdf(self.source, "Acme")
        shutil.rmtree(saved)
        saved.write_bytes(b"KEEP_EXISTING_FILE")
        with self.assertRaises(archive.ArchiveError):
            archive.archive_pdf(self.source, "Acme")
        self.assertEqual(saved.read_bytes(), b"KEEP_EXISTING_FILE")
        saved.unlink()
        target = self.root / "existing folder"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_bytes(b"KEEP_EXISTING_FOLDER")
        self.symlink(saved, target)
        with self.assertRaises(archive.ArchiveError):
            archive.archive_pdf(self.source, "Acme")
        self.assertTrue(saved.is_symlink())
        self.assertEqual(list(target.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"KEEP_EXISTING_FOLDER")
        saved.unlink()
        self.symlink(saved, self.root / "missing target")
        with self.assertRaises(archive.ArchiveError):
            archive.archive_pdf(self.source, "Acme")
        self.assertTrue(saved.is_symlink())

    def test_archive_root_and_parent_symlinks_cannot_redirect_output(self):
        target = self.root / "public folder"
        target.mkdir()
        self.symlink(self.root / "submissions", target)
        with self.assertRaises(archive.ArchiveError):
            archive.archive_pdf(self.source, "Acme")
        self.assertEqual(list(target.iterdir()), [])
        (self.root / "submissions").unlink()
        parent_link = self.root / "redirected checkout"
        self.symlink(parent_link, target)
        with patch.object(archive, "ROOT", parent_link), self.assertRaises(archive.ArchiveError):
            archive.archive_pdf(self.source, "Acme")
        self.assertFalse((target / "submissions").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX file modes")
    def test_new_archive_directories_and_files_are_private(self):
        saved = archive.archive_pdf(self.source, "Acme")
        for directory in (saved.parent, saved):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        for path in saved.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_receipt_write_failure_removes_only_the_new_archive(self):
        previous = archive.archive_pdf(self.source, "Earlier application")
        before = {path.name: path.read_bytes() for path in previous.iterdir()}
        open_file = Path.open

        def fail_receipt(path, *args, **kwargs):
            if path.name == "receipt.json":
                raise OSError("Receipt destination is unavailable")
            return open_file(path, *args, **kwargs)

        with patch.object(Path, "open", fail_receipt):
            with self.assertRaises((archive.ArchiveError, OSError)):
                archive.archive_pdf(self.source, "New application")
        self.assertEqual(list(previous.parent.iterdir()), [previous])
        self.assertEqual({path.name: path.read_bytes() for path in previous.iterdir()}, before)

    def test_source_changed_during_copy_does_not_leave_an_archive(self):
        self.source.write_bytes(self.content + b"x" * (2 * 1024 * 1024))
        source = self.source
        open_file = Path.open

        class ChangingReader:
            def __init__(self, handle):
                self.handle = handle
                self.changed = False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.handle.__exit__(*args)

            def __getattr__(self, name):
                return getattr(self.handle, name)

            def read(self, *args):
                chunk = self.handle.read(*args)
                if len(chunk) > 10 and not self.changed:
                    self.changed = True
                    before = source.stat()
                    with open_file(source, "r+b") as changed:
                        changed.seek(-1, os.SEEK_END)
                        changed.write(b"y")
                    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                return chunk

        def changing_open(path, *args, **kwargs):
            handle = open_file(path, *args, **kwargs)
            return ChangingReader(handle) if path == source and args == ("rb",) else handle

        with patch.object(Path, "open", changing_open):
            with self.assertRaisesRegex(archive.ArchiveError, "changed"):
                archive.archive_pdf(source, "Acme")
        self.assertEqual(list((self.root / "submissions").iterdir()), [])

    def test_cli_success_and_failures_do_not_print_resume_contents(self):
        code, out, err = self.run_main(str(self.source), "--label", "Acme Backend")
        self.assertEqual(code, 0, err)
        self.assertIn("Saved:", out)
        self.assertEqual(err, "")
        self.assertNotIn("PRIVATE_RESUME_CONTENT", out)
        for source in (self.source, self.root / "missing.pdf"):
            code, out, err = self.run_main(str(source), "--label", "Acme Backend")
            self.assertEqual(code, 1)
            self.assertNotIn("Saved:", out)
            self.assertIn("FAIL:", err)
            self.assertNotIn("PRIVATE_RESUME_CONTENT", out + err)

    def test_cli_requires_one_pdf_and_label_and_rejects_output_override(self):
        for args in ([], [str(self.source)], [str(self.source), str(self.source), "--label", "Acme"],
                     [str(self.source), "--label", "Acme", "--output", str(self.root)]):
            with self.subTest(args=args), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    archive.main(args)
            self.assertEqual(caught.exception.code, 2)
        self.assertFalse((self.root / "submissions").exists())

    def test_script_help_runs_without_creating_an_archive(self):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "scripts/archive_resume.py"), "--help"],
            cwd=self.root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--label", result.stdout)
        self.assertIn("header", result.stdout)
        self.assertFalse((self.root / "submissions").exists())

    def test_verify_moved_archive_is_read_only_and_needs_no_original_pdf(self):
        saved = archive.archive_pdf(self.source, "PRIVATE_LABEL Québec")
        backup = self.root / "private backup" / "renamed archive"
        backup.parent.mkdir()
        saved.rename(backup)
        self.source.unlink()
        (backup / "notes.txt").write_text("UNSELECTED_PRIVATE_CONTENT", encoding="utf-8")
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in backup.iterdir()}
        code, out, err = self.run_main("--verify", str(backup))
        self.assertEqual(code, 0, err)
        self.assertIn("byte count and SHA-256 hash match", out)
        self.assertNotIn("PRIVATE", out + err)
        self.assertNotIn("Saved:", out)
        self.assertEqual(err, "")
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "scripts/archive_resume.py"), "--verify", str(backup)],
            cwd=self.root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)
        self.assertEqual({path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in backup.iterdir()}, before)
        self.assertEqual(list((self.root / "submissions").iterdir()), [])

    def test_verify_detects_size_and_same_size_hash_changes_without_writes(self):
        saved = archive.archive_pdf(self.source, "Acme")
        pdf = saved / "resume-acme.pdf"
        for content, message in ((self.content[:-1], "byte count"),
                                 (self.content.replace(b"PRIVATE", b"CHANGED"), "SHA-256 hash")):
            with self.subTest(message=message):
                pdf.write_bytes(content)
                before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in saved.iterdir()}
                code, out, err = self.run_main("--verify", str(saved))
                self.assertEqual(code, 1)
                self.assertIn(message, err)
                self.assertNotIn("PASS:", out)
                self.assertNotIn("PRIVATE", out + err)
                self.assertEqual({path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in saved.iterdir()}, before)

    def test_verify_rejects_malformed_receipts_without_echoing_contents(self):
        saved = archive.archive_pdf(self.source, "Acme")
        receipt = saved / "receipt.json"
        for content in (
            b'{"PRIVATE_LABEL":', b'"PRIVATE_LABEL"', b'[]', b'null', b'\xffPRIVATE_LABEL',
            b'{"pdf": "resume-acme.pdf", "pdf": "PRIVATE_LABEL"}',
        ):
            with self.subTest(content=content):
                receipt.write_bytes(content)
                code, out, err = self.run_main("--verify", str(saved))
                self.assertEqual(code, 1)
                self.assertIn("FAIL:", err)
                self.assertNotIn("PRIVATE_LABEL", out + err)
                self.assertEqual(receipt.read_bytes(), content)

    def test_verify_validates_byte_count_hash_and_required_fields(self):
        saved = archive.archive_pdf(self.source, "Acme")
        receipt = saved / "receipt.json"
        original = json.loads(receipt.read_text(encoding="utf-8"))
        for key, values in (
            ("bytes", (None, True, False, 0, -1, 1.5, str(len(self.content)))),
            ("sha256", (None, True, 12, "", "a" * 63, "a" * 65, "z" * 64)),
            ("pdf", (None, True, 12, "")),
        ):
            for value in values:
                with self.subTest(key=key, value=value):
                    data = dict(original, **{key: value})
                    receipt.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(archive.ArchiveError):
                        archive.verify_archive(saved)
            data = dict(original)
            del data[key]
            receipt.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(missing=key), self.assertRaises(archive.ArchiveError):
                archive.verify_archive(saved)
        original["sha256"] = original["sha256"].upper()
        receipt.write_text(json.dumps(original), encoding="utf-8")
        archive.verify_archive(saved)

    def test_verify_rejects_paths_and_nonportable_filenames_before_opening_pdf(self):
        saved = archive.archive_pdf(self.source, "Acme")
        receipt = saved / "receipt.json"
        original = json.loads(receipt.read_text(encoding="utf-8"))
        open_file = Path.open
        opened = []

        def record_open(path, *args, **kwargs):
            opened.append(path)
            return open_file(path, *args, **kwargs)

        for name in (
            "../chosen.pdf", "/chosen.pdf", "nested/chosen.pdf", "nested\\chosen.pdf",
            "C:\\chosen.pdf", "C:chosen.pdf", "\\\\server\\chosen.pdf", "chosen.pdf:secret.pdf",
            "NUL.pdf", "CON.pdf", "COM1.pdf", "LPT9.pdf", "chosen?.pdf", "chosen*.pdf",
            "chosen|.pdf", 'chosen".pdf', "chosen<.pdf", "chosen>.pdf", "chosen\x00.pdf",
            "chosen\n.pdf", "chosen\u200b.pdf", ".", "..", "chosen.txt", "chosen.pdf ",
        ):
            with self.subTest(name=name):
                receipt.write_text(json.dumps(dict(original, pdf=name)), encoding="utf-8")
                opened.clear()
                with patch.object(Path, "open", record_open), self.assertRaises(archive.ArchiveError):
                    archive.verify_archive(saved)
                self.assertEqual(opened, [receipt])
        self.assertEqual(self.source.read_bytes(), self.content)

    def test_verify_rejects_missing_files_and_directories(self):
        saved = archive.archive_pdf(self.source, "Acme")
        for path in (saved / "resume-acme.pdf", saved / "receipt.json"):
            content = path.read_bytes()
            path.unlink()
            with self.subTest(missing=path.name), self.assertRaises(archive.ArchiveError):
                archive.verify_archive(saved)
            path.mkdir()
            with self.subTest(directory=path.name), self.assertRaises(archive.ArchiveError):
                archive.verify_archive(saved)
            path.rmdir()
            path.write_bytes(content)
        for path in (self.root / "missing archive", self.source):
            code, out, err = self.run_main("--verify", str(path))
            self.assertEqual(code, 1)
            self.assertNotIn("PASS:", out)
            self.assertIn("FAIL:", err)

    def test_verify_does_not_follow_receipt_or_pdf_symlinks(self):
        saved = archive.archive_pdf(self.source, "Acme")
        for path in (saved / "resume-acme.pdf", saved / "receipt.json"):
            content = path.read_bytes()
            outside = self.root / f"outside-{path.name}"
            path.rename(outside)
            self.symlink(path, outside)
            with self.subTest(path=path.name), self.assertRaisesRegex(archive.ArchiveError, "symlink"):
                archive.verify_archive(saved)
            self.assertTrue(path.is_symlink())
            self.assertEqual(outside.read_bytes(), content)
            path.unlink()
            outside.rename(path)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO support")
    def test_verify_rejects_special_files_before_opening_them(self):
        saved = archive.archive_pdf(self.source, "Acme")
        for path in (saved / "resume-acme.pdf", saved / "receipt.json"):
            content = path.read_bytes()
            path.unlink()
            os.mkfifo(path)
            with self.subTest(path=path.name), self.assertRaisesRegex(archive.ArchiveError, "regular file"):
                archive.verify_archive(saved)
            path.unlink()
            path.write_bytes(content)

    def test_verify_permission_errors_do_not_print_private_paths(self):
        saved = archive.archive_pdf(self.source, "Acme")
        with patch.object(Path, "open", side_effect=PermissionError("PRIVATE_LABEL")):
            code, out, err = self.run_main("--verify", str(saved))
        self.assertEqual(code, 1)
        self.assertIn("permissions", err)
        self.assertNotIn("PRIVATE_LABEL", out + err)

    def test_verify_does_not_pass_when_pdf_changes_during_read(self):
        saved = archive.archive_pdf(self.source, "Acme")
        pdf = saved / "resume-acme.pdf"
        digest = hashlib.sha256()

        def change_after_read(chunk):
            digest.update(chunk)
            before = pdf.stat()
            pdf.write_bytes(self.content.replace(b"PRIVATE", b"CHANGED"))
            os.utime(pdf, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))

        with patch.object(archive.hashlib, "sha256") as hashing:
            hashing.return_value.update.side_effect = change_after_read
            hashing.return_value.hexdigest.side_effect = digest.hexdigest
            code, out, err = self.run_main("--verify", str(saved))
        self.assertEqual(code, 1)
        self.assertIn("changed during verification", err)
        self.assertNotIn("PASS:", out)

    def test_verify_cli_is_exclusive_with_archive_arguments(self):
        for args in (("--verify",), ("--verify", str(self.root), "--label", "Acme"),
                     (str(self.source), "--verify", str(self.root))):
            with self.subTest(args=args), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    archive.main(args)
                self.assertEqual(caught.exception.code, 2)
        self.assertFalse((self.root / "submissions").exists())

    @unittest.skipUnless(os.name == "posix", "Replacing open files requires POSIX semantics")
    def test_verify_rejects_atomic_replacement_even_with_stable_open_file_stats(self):
        saved = archive.archive_pdf(self.source, "Acme")
        pdf = saved / "resume-acme.pdf"
        receipt = saved / "receipt.json"
        original_stat = pdf.stat()
        receipt_before = receipt.read_bytes(), receipt.stat().st_mtime_ns
        replacement = saved / "replacement.pdf"
        changed = self.content.replace(b"PRIVATE", b"CHANGED")
        replacement.write_bytes(changed)
        replacement_stat = replacement.stat()
        digest = hashlib.sha256()

        def replace_after_read(chunk):
            digest.update(chunk)
            replacement.replace(pdf)

        with patch.object(archive.hashlib, "sha256") as hashing, \
                patch.object(archive.os, "fstat", return_value=original_stat):
            hashing.return_value.update.side_effect = replace_after_read
            hashing.return_value.hexdigest.side_effect = digest.hexdigest
            code, out, err = self.run_main("--verify", str(saved))
        self.assertEqual(code, 1)
        self.assertIn("changed during verification", err)
        self.assertNotIn("PASS:", out)
        self.assertEqual((pdf.read_bytes(), pdf.stat().st_mtime_ns), (changed, replacement_stat.st_mtime_ns))
        self.assertEqual((receipt.read_bytes(), receipt.stat().st_mtime_ns), receipt_before)
        self.assertEqual({path.name for path in saved.iterdir()}, {pdf.name, receipt.name})


if __name__ == "__main__":
    unittest.main()
