# Template Checks

The browser reviewer has a separate [test suite](../tools/pdf-review/README.md#development) for Chromium, Firefox, and WebKit. Its dependencies are not needed for `make test`. Neither suite tests GitHub's embedded PDF viewer.

Upload-limit checks cover exact byte boundaries, fractional MB, invalid inputs, replacement files, clearing, keyboard use, and narrow screens. File and hosted-page tests also check for network requests and browser storage.

`make test` builds all starters, runs unit tests, checks PDFs, headings, and contact links, compiles the starter ZIPs, tests placeholder and page-limit warnings, and exercises the personal PDF checker. It needs XeLaTeX, `latexmk`, Python 3.9+, and Poppler's `pdftotext` and `pdfinfo` on `PATH`; no pip packages.

The check compares every page with `expected/*.txt` using Poppler's `-layout` reading order. Missing or reordered words, changed punctuation, unmapped characters, and extra or missing pages fail. Whitespace and Unicode ligature differences are ignored. Line-end hyphens are preserved.

Inspect the PDF too: extraction tests cannot catch every visual defect or predict how other parsers read it.

## Run without make

Build the PDFs first, then run from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/check_pdf_text.py
python3 tests/check_pdf_text.py --no-internship output/pdf/no-internship-resume.pdf --new-grad output/pdf/new-grad-resume.pdf --experienced output/pdf/experienced-resume.pdf --ai-engineer output/pdf/ai-engineer-resume.pdf --ml-engineer output/pdf/ml-engineer-resume.pdf --graduate-admissions output/pdf/graduate-admissions-resume.pdf
python3 scripts/check_resume.py output/pdf/no-internship-resume.pdf --max-pages 1
python3 scripts/check_resume.py output/pdf/new-grad-resume.pdf --max-pages 1
python3 scripts/check_resume.py output/pdf/experienced-resume.pdf --max-pages 2
python3 scripts/check_resume.py output/pdf/ai-engineer-resume.pdf --max-pages 1
python3 scripts/check_resume.py output/pdf/ml-engineer-resume.pdf --max-pages 1
python3 scripts/check_resume.py output/pdf/graduate-admissions-resume.pdf --max-pages 1
python3 scripts/package_templates.py --check
python3 tests/check_starter_builds.py
python3 tests/check_placeholders.py
python3 tests/check_layout.py
python3 tests/check_page_limits.py
python3 tests/check_contacts.py
python3 tests/check_ai_ml.py
python3 tests/check_graduate_admissions.py
```

On Windows, use `py -3` instead of `python3`. The PDF checker accepts `--no-internship`, `--new-grad`, `--experienced`, `--ai-engineer`, `--ml-engineer`, and `--graduate-admissions` for other locations.

## Starter downloads

Run `make downloads` to rebuild the starter ZIPs and the optional application-versions ZIP in `downloads/`. Without make, run `python3 scripts/package_templates.py` for the starters and `python3 scripts/package_application_versions.py` for the shared-content example.

Each regular starter archive contains only the chosen template as `resume.tex`, the shared class, compiler config, start guide, and license. Text is UTF-8 with LF line endings. Fixed ZIP metadata keeps builds identical across checkouts.

`make test-downloads` fails if a ZIP is missing, stale, or contains extra files. It does not regenerate downloads, so CI cannot hide an outdated archive by rebuilding it.

`make test-starters` unpacks the checked-in ZIPs into temporary folders and runs `latexmk resume.tex`. No source files are copied in. This tests the bundled compiler config and applies the same PDF checks to what users download. Temporary builds are deleted when the check ends.

## Placeholder warnings

`make test-placeholders` compiles small fixtures with XeLaTeX. Sample names, hidden contact URLs, example entry fields, and bracketed prompts must warn. Completed content, comments, and command options must not. The checks also compare extracted text with reminders enabled and disabled.

The shipped templates intentionally contain placeholders, so their warnings are expected. Reminders do not block compilation or certify that a resume is ready. They inspect the template commands and lists, not arbitrary macros or every word in the document.

## Entry layout

`make test-layout` compiles long employer, university, location, and date fields on Letter and A4, including missing locations and dates. It rejects overfull boxes, missing or duplicated words, overlapping word bounds, and text outside the margins. A page-end fixture checks that a wrapped heading moves with its role.

Wrapped columns can interleave in layout-mode extraction. These stress tests check word completeness and bounds, not semantic reading order. The shipped templates still use exact page snapshots. Inspect rendered pages before accepting layout changes.

## Page-limit warnings

`make test-page-limits` checks one- and two-page budgets, extra pages, changed budgets, and invalid inputs. Fixtures cover a first build, a shortened rebuild, reset page numbers, discarded pages, and content added at the end of a document. It also checks that enabling reminders leaves extracted text unchanged.

The class reads LaTeX's shipped-page counter after the final page. It does not infer length from printed page numbers or a previous build. A missing budget disables the check; invalid values warn without replacing the last valid budget. Starters use one page, except the experienced template's two.

Resolve LaTeX rerun warnings before checking the final length. When a last-page hook needs another run, the kernel can append a temporary page outside its shipped-page counter. A regression covers a two-page document shortened to one: the temporary page disappears on the next run and the settled count is correct.

## Contact links

`make test-contacts` compiles email and phone examples, then checks their visible text with `pdftotext` and actual link destinations with `pdfinfo -url`. Both tools come with Poppler. Tests cover edited values, email punctuation, phone formatting, placeholder reminders, and unsupported inputs. These checks do not verify that an inbox or phone number belongs to you; click your final PDF's links too.

## AI and ML starters

`make test-ai-ml` compiles both role starters on Letter and A4. It checks page bounds, overlapping words, contact destinations, placeholder warnings, and section order. It also compiles education-first versions and the exact research block from the guide in place of the ML project. No new LaTeX package is required.

The default role templates contain no research or publication claims. Their source, published PDFs, and ZIP builds use `expected/ai-engineer-1.txt` and `expected/ml-engineer-1.txt`. `make preview-ai-ml` refreshes only their PDFs and previews.

## Graduate admissions starter

`make test-graduate-admissions` checks the default CV on Letter and A4, optional publication/presentation blocks, a two-degree CV, and a project-first adaptation without research or teaching. It checks page counts, text bounds, contact destinations, and placeholder warnings. `make preview-graduate-admissions` refreshes only this starter's PDF and PNG; its text baseline is `expected/graduate-admissions-1.txt`.

## Shared-content application versions

`make test-application-versions` checks the optional project separately from the regular starters. It checks the ZIP against an explicit source allowlist, compiles all three source and downloaded versions, and compares their text with `expected/application-*-1.txt`.

Fixtures cover shared contact, date, and education edits; selected and unselected bullets; changed selection order; unknown commands; placeholder warnings; and Letter/A4 page bounds. The source ZIP contains the full bullet bank, while each PDF must contain only its selected bullets.

Without make:

```bash
python3 scripts/package_application_versions.py --check
python3 tests/check_application_versions.py
python3 tests/check_application_versions.py --published
```

After changing the example, run `make preview-application-versions` and inspect all three pages. Review their extracted text before updating the matching baselines. Run `make application-download`, then `make test-application-versions`. The other starter baselines should not change.

## Change a baseline

After an intentional template edit:

1. Run `make preview` and inspect every page.
2. Read the extracted text with `pdftotext -layout path/to/resume.pdf -`.
3. Update the affected page in `expected/` with the reviewed text, without the trailing form feed. Keep dates on the same line as the organization, as layout mode emits them.
4. Run `make downloads`, then `make test`. Commit the source, refreshed previews/PDFs, ZIPs, and baseline together.

Do not accept a new baseline just to clear a failure. Check it against the source and rendered page.

## Check your own resume

The snapshots above describe the shipped templates, not your edited resume. Use the separate checker instead:

```bash
python3 scripts/check_resume.py "path/to/your-resume.pdf" --max-pages 1
```

It requires only Python 3.9+ and Poppler, not TeX or the snapshot files. [Install the dependencies](../docs/local-setup.md#pdf-checker-dependencies). Omit `--max-pages` for no page limit. For a filename starting with a dash, use `python3 scripts/check_resume.py --max-pages 1 -- -resume.pdf`.

The check fails on unreadable or empty files, Poppler errors or warnings, empty text pages, replacement/private-use/control characters, and a page count above your chosen limit. Whitespace, ligatures, punctuation, and language-specific format characters are allowed. Errors name the page or character code, not the surrounding text. Exit codes: `0` passed these checks, `1` failed a check, `2` invalid command arguments.

It runs locally and does not upload, print, or save extracted text. It cannot detect missing words, wrong reading order, clipping, false claims, or ATS compatibility. A pass is not a resume score. Inspect the PDF and read its text:

```bash
pdftotext -layout "path/to/your-resume.pdf" -
```

Check your name, email, dates, headings, bullet order, and text split across pages. This manual command prints personal data; redact it before opening an issue. Do the same with snapshot failure diffs, which quote template text.

`make test-personal-pdf` runs the checker against all published starter PDFs. Unit tests cover blank pages, character handling, corrupt/locked files, timeouts, missing tools, command arguments, standalone use, and private-data suppression. Neither check writes to the input PDF.
