# Before you send

Review the exact PDF you plan to upload. Repeat after any edit.

## Checklist

1. **Rebuild from the final source.** In Overleaf, recompile with XeLaTeX and download the PDF. Locally, run `latexmk -g resume.tex`. A failed build can leave an older PDF behind, so check the log before downloading.
2. **Clear the log.** Replace every flagged placeholder or delete the entry. Fix unlinked contacts. If the resume ran past its page budget, cut less relevant content rather than shrinking the type.
3. **Read every page.** Check names, dates, headings, bullet order, and the footer on a second page. Look for clipped or overflowing text.
4. **Click every link.** Email, phone, and profile links must open the right destination.
5. **Read the extracted text.** Open the PDF in the [offline reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip) (unzip, open `pdf-review.html`) or run `pdftotext -layout resume.pdf -`. A parser reads this text, so it should match the page in order and content. Scanned pages have no text; nothing here runs OCR.
6. **Check the file.** The PDF title is your name followed by Resume. These resumes are small, usually well under 100 KB, so portal size limits are rarely a problem.

## If the log shows a reminder

- **Placeholder reminder in ...:** sample text remains in that field. Literal square brackets also trigger it.
- **Unsupported email or phone format:** the contact printed without a link. Fix the value or use `\resumelink{destination}{label}`.
- **Missing character:** the font has no glyph for a symbol. Replace the symbol or choose a font that has it.
- **Overfull \hbox:** text ran past the margin. Shorten the unbroken text named in the log.
- **Page limit exceeded:** the PDF has more pages than `\resumepagelimit{N}` allows.

## From a repository checkout

Build and check one source in one command:

```bash
python3 scripts/review_resume.py templates/new-grad-resume.tex --max-pages 1
```

It compiles with XeLaTeX into an ignored folder, summarizes the warnings above, and checks that every page has extractable text. Add `--export-pdf "~/Applications/Acme-Resume.pdf"` to copy the checked PDF to a new file; existing files are never replaced. Add `--max-size-mb 2` when a portal states a size limit. The command needs Python 3.9+, `latexmk`, XeLaTeX, and Poppler. [Local setup](local-setup.md).

To check a PDF you already have:

```bash
python3 scripts/check_resume.py "path/to/resume.pdf" --max-pages 1
```

## Keep the PDF you sent

Save the uploaded file in a private folder named with the date, company, and role, such as `2026-11-06 Acme backend engineer.pdf`. Keep every revision. Rebuilding later should not change the copy you prepare interviews from.
