# Before you send

Review the exact PDF you plan to upload. Repeat after any edit.

## 1. Rebuild the chosen source

**Overleaf:** select your main document and XeLaTeX, recompile, then download the PDF. For an application version, select its entry file, such as `backend.tex`.

**Local starter:** run `latexmk -g -halt-on-error resume.tex` in the extracted folder. Substitute the entry filename for a named application version.

A failed build can leave an older preview or PDF. Continue only after a successful build and check that it is the intended version.

**From a repository checkout**, the final-review command builds one source and summarizes its warnings:

```bash
python3 scripts/review_resume.py templates/new-grad-resume.tex \
  --max-pages 1 --max-size-mb 2
```

Replace the source path with your `.tex` entry file, including one outside the checkout. Use the application's limits; omit either option if none is specified. MB means 1,000,000 bytes. Exact-size files pass; one byte over fails.

The command needs Python 3.9+, `latexmk`, XeLaTeX, and Poppler's `pdftotext`. See [local setup](local-setup.md). Each run uses a fresh folder under ignored `.context/final-review/` and prints its logs and PDF path.

To save an edited resume under your upload filename, add `--export-pdf`:

```bash
python3 scripts/review_resume.py "/path/to/your/resume.tex" \
  --max-pages 1 --max-size-mb 2 --export-pdf "~/Applications/Resume.pdf"
```

Create the destination folder first. Export copies this run's PDF only after checks finish without reported source reminders; existing files are never replaced. Use a local folder that supports hard links. The exported PDF still needs the manual review below.

## 2. Resolve reminders and page limits

- **Placeholders:** replace flagged sample values or delete unused entries, including those in shared content files. Literal brackets can trigger reminders; unmarked sample text can be missed.
- **Unlinked contacts:** correct the email or include the phone's country code. For other formats, use `\resumelink{destination}{label}` and check the exported link.
- **Overflow:** inspect the affected page and log line. Shorten unbroken text or adjust the entry, then rebuild.
- **Page limits:** cut less relevant content or allow another page if the application permits it. The source's `\resumepagelimit{N}` takes a positive whole number. The command's `--max-pages N` checks the exported PDF separately.

Let LaTeX finish requested reruns before judging page count. Read the full log for warnings the summary does not cover.

The command exits with `0` for completed checks, `3` for source reminders, `1` for a failed build or PDF check, and `2` for invalid arguments. Continue with the manual review below even after exit `0`.

## 3. Read the extracted text

[Download the offline reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip), unzip it, open `pdf-review.html`, and choose **Open PDF**.

Compare every page's extracted text with the PDF: names, contacts, dates, headings, bullet order, missing words, and odd symbols. The automated checks cannot establish completeness or correct reading order. If text is missing or extraction fails, fix the source or font problem and rebuild. Scanned pages need a text layer; the reviewer does not run OCR.

After tailoring, use **Compare two exports** to keep the earlier PDF, then open the revised export. Check changed wording and link destinations; compare layout yourself.

## 4. Inspect the final PDF and links

Check every page for clipping, overflow, unwanted pages, and incorrect content. Use **Show on page** to compare each link destination with its printed label and clickable area.

The reviewer does not follow links. Click them in your PDF reader to verify the destinations. Use **Application upload limits** for the portal's page and file-size limits. See the [reviewer's limits](../tools/pdf-review/README.md) if it cannot open your file.

These checks do not assess hiring outcomes or ATS compatibility.

## 5. Keep the submitted copy

Upload the reviewed PDF, then [save that exact file with the company and role](submitted-resumes.md). Keep it separate from future rebuilds for interview preparation.
