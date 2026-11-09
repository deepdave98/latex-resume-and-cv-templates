# Keep the PDF you submitted

After uploading a resume, save that exact PDF with the company and role. Rebuilding a resume later should not change the copy you use to prepare for an interview.

## From Overleaf or a PDF download

Open the PDF you uploaded in the [offline reviewer](../tools/pdf-review/README.md). After reviewing it, expand **Submitted copies**, enter the company and role, and choose **Save copy (.zip)**.

Keep the ZIP privately and unzip it when needed. Its dated folder contains the original PDF and `receipt.json`, compatible with the verification command below. The PDF's metadata and password protection remain; text edits made in the reviewer are excluded. The browser controls the download filename and location, so check where it saved the ZIP and keep each revision separately.

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

To keep submissions outside the checkout, choose an existing private folder:

```bash
python3 scripts/archive_resume.py "/path/to/submitted-resume.pdf" \
  --label "Acme - Backend Engineer" --output-dir "~/Applications/Submitted"
```

The dated folder is created inside `Submitted`. The parent must already exist; existing files and folder permissions stay unchanged. Relative paths start from your current working directory. Choose a location you back up privately; `--output-dir` does not add Git ignore rules.

## Verify a saved copy

**In the browser:** unzip the saved copy, open its PDF in the reviewer, then expand **Submitted copies** and choose **Choose receipt.json**. Select the receipt from that same folder. The reviewer compares the opened PDF's original bytes, excluding text edits. Renaming the PDF is allowed; the filename recorded in the receipt is shown separately. Receipts must be no larger than 64 KiB.

**In a repository checkout:** pass the saved folder, including an unzipped browser download or a backup moved outside this checkout:

```bash
python3 scripts/archive_resume.py --verify "submissions/2026-10-22-acme-backend-engineer"
```

Both methods compare the PDF's byte count and SHA-256 with `receipt.json` and change no files. The terminal command expects the recorded filename; missing files, malformed receipts, or mismatches return exit code `1`, and a match returns `0`. If a check fails, compare with a trusted backup before replacing either file.

A match does not authenticate the label/date or prove delivery. A receipt is not a signature: someone who changes both files can replace the record.

Keep a private backup outside this checkout before deleting or replacing it. Git ignores `submissions/`, so pushing this repository does not back it up. Receipts are not encrypted. Any PDF password protection stays intact; files can still be edited or deleted.

## Copy manually

Copy the uploaded PDF into a private folder named with the date, company, and role. Keep a different folder for each revision and never replace an earlier submission.

For a manual copy without a receipt, record its hash with `shasum -a 256 file.pdf` on macOS/Linux or `Get-FileHash file.pdf -Algorithm SHA256` in PowerShell. Compare it again later to detect changed bytes; no checkout is needed.
