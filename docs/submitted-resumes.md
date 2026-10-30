# Keep the PDF you submitted

After uploading a resume, save that exact PDF with the company and role. Rebuilding a resume later should not change the copy you use to prepare for an interview.

## From a repository checkout

Use the PDF you uploaded, including the specific output path printed by the [final-review command](before-you-send.md) if you used it:

```bash
python3 scripts/archive_resume.py "/path/to/submitted-resume.pdf" \
  --label "Acme - Backend Engineer"
```

The command needs Python 3.9+ and no other tools. It saves two files under the checkout's ignored `submissions/` folder:

```text
submissions/2026-10-22-acme-backend-engineer/
  resume-acme-backend-engineer.pdf
  receipt.json
```

The date is the local date when you save the copy. The receipt records the label, save time with time zone, PDF filename, byte count, and SHA-256 hash. It contains no source path or resume text. Only the selected PDF is copied; source files and unused bullets stay out of the archive.

An existing date and label will not be overwritten, even if the PDF changed. Use a distinct label such as `Acme - Backend Engineer - revised` for a later submission that day. Spaces and punctuation become hyphens in filenames; the receipt retains your label. Long labels are shortened for filenames, so different labels can resolve to the same destination; the command refuses that collision too.

The command checks the PDF header and copies its bytes. It does not validate or upload the document. Finish the [PDF review](before-you-send.md) first.

## Verify a saved copy

Pass the saved folder, including a backup moved outside this checkout:

```bash
python3 scripts/archive_resume.py --verify "submissions/2026-10-22-acme-backend-engineer"
```

This compares the named PDF's byte count and SHA-256 with `receipt.json` and changes no files. Missing files, malformed receipts, or mismatches return exit code `1`; a match returns `0`.

A match does not authenticate the label/date or prove delivery. A receipt is not a signature: someone who changes both files can replace the record.

Keep a private backup outside this checkout before deleting or replacing it. Git ignores `submissions/`, so pushing this repository does not back it up. These are ordinary local files, not encrypted or locked against manual edits.

## From Overleaf

Download the reviewed PDF and upload that file to the application. Copy the same download into a private folder named with the date, company, and role. Keep a different folder for each revision and never replace an earlier submission.

For a manual copy without a receipt, record its hash with `shasum -a 256 file.pdf` on macOS/Linux or `Get-FileHash file.pdf -Algorithm SHA256` in PowerShell. Compare it again later to detect changed bytes; no checkout is needed.
