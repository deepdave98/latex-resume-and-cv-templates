# Before you send

Review the exact version you plan to upload. Repeat these steps after any edit.

## 1. Rebuild the chosen source

**Overleaf:** choose your main document (`resume.tex`, or a named version such as `backend.tex`) and use XeLaTeX. Recompile, check the log, and confirm that the preview contains the intended version before downloading its PDF. If compilation fails, fix the reported source and line, then recompile. An older preview or download is not evidence of a successful build.

**Local starter:** in the extracted folder, run `latexmk -g -halt-on-error resume.tex`. For an application version, use its entry file instead. Continue only after a successful build; check the matching `.log` and `.pdf` (for example, `backend.log` and `backend.pdf`). A failed build can leave an older PDF in place.

**Optional local summary:** from a repository checkout, this command builds only the source you name:

```bash
python3 scripts/review_resume.py templates/new-grad-resume.tex --max-pages 1
```

For a named application version or an edited starter outside the checkout, choose that file instead:

```bash
python3 scripts/review_resume.py examples/application-versions/backend.tex --max-pages 1
python3 scripts/review_resume.py "/path/to/extracted-starter/resume.tex" --max-pages 1
```

This needs Python 3.9+, `latexmk`, XeLaTeX, and Poppler's `pdftotext` on `PATH`. If a tool is missing, follow [local setup](local-setup.md), including its [PDF checker dependencies](local-setup.md#pdf-checker-dependencies), then retry.

Each run uses a fresh directory under ignored `.context/final-review/`. It prints the source, build log, LaTeX log, and exact PDF path. It does not update published PDFs, previews, or downloads. On a compile failure, read the build log, correct the source, and retry; the command will not accept an older PDF as this run's output.

## 2. Resolve reminders and page limits

- **Placeholders:** replace the flagged sample text or delete unused entries, then rebuild. Check included content files too. Reminders inspect selected template commands and lists; they can miss unfinished text, and literal brackets can trigger them.
- **Unlinked contacts:** an unsupported email or phone value prints without a clickable link. Correct the literal email or include the phone country code. For other formats, use `\resumelink{destination}{label}` and check the exported PDF's links.
- **Overflow:** an overfull box can put content beyond its available space. Inspect the affected page and log line, shorten unbroken text or adjust the entry, then rebuild. A clean log still does not prove the layout is correct.
- **Too many pages:** remove less relevant content, or allow another page when the application permits it. The source uses `\resumepagelimit{1}` (in `setup.tex` for the application-version example). Change it only when the longer version is intentional. An invalid source limit needs a whole number from 1 to 999999999.
- **Command page limit:** `--max-pages 1` separately checks the built PDF's page count. Omit it for no additional command limit. Source reminders still apply; no warning does not prove that a source limit was set.

Let requested LaTeX reruns finish before judging page count. Review other log warnings against the PDF too.

The local command exits with `0` when its checks finish without reported reminders, `3` when source reminders need review, `1` when a build or PDF check fails, and `2` for invalid arguments. None of these outcomes replaces the checks below.

## 3. Read the extracted text

[Download the offline reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip), unzip it, and open `pdf-review.html`. Choose **Open PDF** and select the newly built or downloaded PDF.

Read every page's extracted text. Check names, contacts, dates, headings, bullet order, missing words, and odd symbols against the PDF. The local command checks for empty text pages, flagged characters, and extraction errors; it cannot establish completeness or correct reading order.

If extraction fails or text is missing, open the PDF to confirm it is readable, inspect the reported page, and correct the source or font problem before rebuilding. Image-only pages need a text layer; the reviewer does not run OCR. If Poppler reports an error, check its message and whether the PDF is password-protected. A failed extraction leaves the text review unfinished.

## 4. Inspect the final PDF and links

In the reviewer, inspect every rendered page for clipping, overflow, unwanted pages, and incorrect content. Under link destinations, use **Show on page** to compare each destination with its printed label and clickable area.

The reviewer does not follow links or check whether a website is online. Open the same PDF in a PDF reader and click its links to verify their destinations. Use **Application upload limits** if the portal specifies page or file-size limits. See the [reviewer's limits](../tools/pdf-review/README.md) if it cannot open your file.

Upload the PDF you just reviewed. These checks do not assess hiring outcomes or ATS compatibility.

## 5. Keep the submitted copy

After uploading, [save the exact PDF with the company and role](submitted-resumes.md). Keep it separate from future rebuilds so you can refer to the same version when preparing for an interview.
