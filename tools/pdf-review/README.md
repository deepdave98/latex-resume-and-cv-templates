# PDF review

Read a resume PDF beside its extracted text and inspect its links.

## Use it

1. [Download the reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip), unzip it, and open `pdf-review.html` in a current Chrome, Edge, Firefox, or Safari browser.
2. Choose **Open PDF** or drop one file onto the file bar.
3. Read each page and its text. Use **Show on page** to locate a link.
4. Open **Text for application forms** to edit a text copy. **Copy all text** copies it; **Save .txt** downloads it; **Reset text** restores the extraction. The PDF and per-page text stay unchanged.

Works offline with one PDF at a time, up to **20 MiB (20,971,520 bytes) and 20 pages**. Password-protected files ask for the password locally.

Opening another file, **Clear file**, and **Reset text** ask before discarding edits, even after copying or saving. Cancelling or dropping several files keeps the current review. Copy or save before leaving: browsers may suppress the leave-page warning. If processing fails after you edit text, those edits remain available; the page review is incomplete.

## Compare two exports

1. Open the earlier PDF, expand **Compare two exports**, and choose **Keep this PDF as before**.
2. Open the revised export.
3. Check changed wording, external destinations and their counts, page counts, and exact file sizes. Inspect both PDFs for layout changes.

Comparison uses original extracted text, excluding application-form edits. Whitespace is ignored; punctuation, numbers, capitalization, and Unicode are preserved. Reordered words appear as removals and additions. Raw and resolved link destinations are both compared.

Missing, broken, truncated, or oversized data produces an incomplete result. Form fields may be absent from text; internal links and PDF actions cannot be compared. **No differences in extracted text** does not establish that the PDFs look alike or contain the same information.

**Use current PDF as before** replaces the reference; **Forget before copy** removes it. Cancelled or failed replacements keep it.

## Application upload limits

Enter the portal's maximum pages and file size under **Application upload limits**. Leave either blank to skip it. Limits are inclusive; one byte over is flagged. Nothing is trimmed or compressed.

Use a whole number for pages and a positive number such as `0.5` for MB. Size uses **decimal MB (1 MB = 1,000,000 bytes)** and shows the exact bytes. Check the portal's units and other requirements too.

Page, size, and character limits carry over to another PDF. Clearing, reloading, or closing resets them, as does a file that cannot open. If processing fails after text edits, the draft and its limits remain available.

## Application text limits

Enter a **Character limit (optional)** to see remaining or excess characters. It never cuts text or blocks copying and saving. Resetting text keeps the limit.

Counts use [UTF-16 code units](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/maxlength). Spaces and line breaks count; emoji and some accented characters use multiple units. Check the form's own counter. Text edits are capped at 500,100 units.

## What to check

- **Extracted text:** compare names, words, symbols, and reading order with the PDF. Ligatures such as `ﬁ` become ordinary letters. Missing text, form fields, and truncation need manual review; scans need a text layer. There is no OCR or ATS test.
- **Links:** use **Show on page** to compare a destination with its printed label and clickable area. **Back to link** returns to the row; selecting the same button clears the highlight. Hidden controls appear as escapes. Links stay inert: open the PDF in a reader to test them.
- **File properties:** inspect stored titles, authors, and creating applications for old names. PDF Info and XMP are shown separately. Only common fields are read; metadata is not removed.
- **Sample contacts:** flagged starter email, phone, or profile destinations need replacing. This catches known samples only.
- **Blank pages:** preview-based hints can miss faint content. A failed preview is never treated as blank.
- **Paper size:** check dimensions and orientation against the application requirements. Measurements include cropping, rotation, and PDF scale.

Link highlights follow annotation bounds, which may cover images or broad areas. Missing or off-page bounds get warnings. Use **Enlarge** for small labels and **Fit page** to restore the view.

## Privacy

PDFs, passwords, names, and links stay in browser memory. There are no uploads, analytics, cookies, browser storage, or service workers. PDF links and scripts are not executed; the page's security policy blocks network connections.

Clearing, reloading, or closing discards the review and comparison. Nothing is saved automatically. This is not a secure memory wipe and cannot control extensions or the operating system. A static host can receive page-request data, but not the PDF.

Copied text may remain in clipboard history. **Save .txt** creates a UTF-8 download containing only your text, without review warnings. Clearing the page does not delete that file; check it before sending.

## Development

Requires Node.js 22.13+; CI uses Node.js 24:

```bash
cd tools/pdf-review
npm ci --ignore-scripts
npm run build
npm test
npx playwright install --with-deps chromium firefox webkit
npm run test:browser
npm run check
```

`build` writes the self-contained HTML and a reproducible ZIP to `downloads/`. Commit the ZIP, not the generated HTML. `check` rebuilds in memory and fails if the committed ZIP is stale. Browser tests cover both a local file and a website, including offline processing. Tests use public templates and synthetic fixtures, never personal resumes.

Tests run in Chromium, Firefox, and WebKit. Chromium and Firefox use offline emulation. WebKit blocks all HTTP(S) instead because its offline emulation also blocks local blob workers. Every engine checks for zero post-load network requests and no browser storage.

Interface checks cover file selection, copying without opening the text disclosure, clipboard failure, link highlighting, keyboard controls, rotation, clearing, and narrow screens. Synthetic fixtures cover multi-page PDFs. For visual review, open the public PDFs at desktop and phone widths. Check the first page is visible without scrolling past instructions, text and URLs wrap, and selecting a link identifies the right area. Repeat with an unreadable PDF and a scan; neither should look like a successful text check.

For a local preview, run `node server.mjs` and open `http://127.0.0.1:4178/`. The server serves only the generated page; it has no upload route.

| File | Purpose |
| --- | --- |
| `index.html`, `styles.css` | Interface and copy |
| `src/app.mjs` | File lifecycle, worker, previews, clipboard, and DOM |
| `src/review.mjs` | Bounded text and annotation inspection |
| `src/link-region.mjs` | Annotation coordinates clipped to the rendered page |
| `src/compare.mjs`, `src/comparison-view.mjs` | Bounded comparisons of original text and external destinations |
| `src/document-properties.mjs` | Bounded, on-demand inspection of PDF Info and XMP fields |
| `src/page-size.mjs` | Paper names, dimensions, and orientation from PDF page geometry |
| `src/text-download.mjs` | UTF-8 text exports and safe download names |
| `src/text-limits.mjs` | Character counts and optional application-text limits |
| `src/upload-limits.mjs` | Optional page and file-size comparisons |
| `build.mjs` | Embedded PDF.js resources, CSP hashes, and ZIP |
| `tests/` | Unit, package, privacy, and browser checks |

PDF.js is pinned in `package-lock.json`. Update it through a dependency PR, rebuild the ZIP, and run all checks. Its license and bundled font/decoder notices are included under **PDF engine and licenses** in the page. The app code uses the repository's MIT license; bundled third-party code retains its own licenses.

## Optional hosting

The same HTML works on a static host. No backend is needed. Do not add analytics or third-party scripts.

Enable **Settings → Pages → Source: GitHub Actions**, then run **Publish PDF review** from the Actions tab on `main`. It publishes only the reviewer. Rerun it after reviewer updates; downloaded copies do not update themselves.
