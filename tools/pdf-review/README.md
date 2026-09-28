# PDF review

Read a resume PDF beside its extracted text. Check where each link points and where it appears on the page.

## Use it

1. [Download the reviewer](https://raw.githubusercontent.com/deepdave98/swe-resume-templates/main/downloads/pdf-review.zip).
2. Unzip it. Open `pdf-review.html` in a current Chrome, Edge, Firefox, or Safari browser.
3. Choose **Open PDF** or drop your file onto the file bar.
4. Read each page and its text. Use **Show on page** to locate a link.
5. Open **Text for application forms** to edit a text copy. **Copy all text** copies that version; **Save .txt** downloads it. **Reset text** restores the extraction. The PDF and per-page text stay unchanged.

No install, terminal, account, or internet connection is needed after downloading. Keep the HTML file and use it again. It includes the PDF engine, fonts, and decoding resources; it does not load them from a CDN.

One PDF at a time, up to 20 MB and 20 pages. Password-protected files ask for the password locally. **Clear file** discards the review and text edits; choosing another file replaces them. Copy or save edits first.

## What to check

- **Extracted text:** look for missing words, odd symbols, and wrong reading order. Text order comes from the PDF, not from a guess about its layout. Ligatures such as `ﬁ` become ordinary letters for copying.
- **Link destinations:** select **Show on page** beside a destination. Its clickable area is highlighted in the preview so you can compare it with the printed label. **Back to link** returns to that row. Select the same button again to clear the highlight. Destinations remain text only; the tool never follows them or checks whether a website is online. Hidden control characters are shown as escapes. Internal links and unsupported PDF actions are identified separately.
- **Pages without text:** a scan or outlined lettering may look fine but copy nothing. This tool does not run OCR.
- **Pages that appear blank:** this is a preview-based hint, not proof. Very faint content can be missed. A failed preview is never counted as a blank page.
- **File properties:** open the disclosure to inspect title, author, subject, keywords, creating application, producer, and dates. PDF Info and selected XMP values appear separately, so conflicting values remain visible. Dates are shown as stored; hidden control characters are escaped. A software name in Creator or Producer is not an error.

Properties are read only when you open that section. This does not inspect custom metadata, embedded files, comments, or revision history, and it does not remove anything. Missing fields are not proof that a PDF is safe to share. Long values are capped at 1,024 characters and author lists at 16 entries; truncation or unreadable fields are identified. A failed property read leaves the page review available.

Form fields, incomplete extraction, and truncated results get warnings. Review the original PDF if anything is missing. PDF.js and Poppler can produce different text order; neither predicts how every application form or ATS will parse a file. There is no resume score.

Link highlights use the PDF's annotation bounds, not guessed text matches. A PDF can attach a link to a broad area, an image, or no visible label. Missing or off-page bounds get a position warning; a failed preview never gets a highlight. Highlights follow rotated and cropped pages and scale with the preview. Use **Enlarge** to read small labels; **Fit page** restores the full-page view. Neither changes the PDF.

## Privacy

The PDF is read from the browser's file picker into memory. No upload endpoint, analytics, cookies, browser storage, or service worker. No filename, password, text, or link destination is sent anywhere. Links and PDF scripts are not executed.

The page's Content Security Policy blocks network connections, external scripts, form submission, and plugins. The PDF worker runs locally. Closing, reloading, or clearing the page discards this tool's review. This is not a secure memory wipe, and it cannot control browser extensions or your operating system.

Copying text puts it on your system clipboard. Other apps or clipboard history may retain it. **Save .txt** creates a UTF-8 file in your browser's download location; clearing the review does not delete that file. Exports contain only the text copy, without the reviewer’s warnings or labels. Check it against the PDF, especially if extraction was incomplete. Text edits are limited to 500,100 UTF-16 code units.

If someone hosts this page, their host can receive normal page-request data; it still does not receive your PDF.

## Development

End users need only the download. Maintainers need Node.js 24+:

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

Interface checks cover file selection, copying without opening the text disclosure, clipboard failure, link highlighting, keyboard controls, rotation, clearing, and narrow screens. For visual review, open the public one- and two-page PDFs at desktop and phone widths. Check the first page is visible without scrolling past instructions, text and URLs wrap, and selecting a link identifies the right area. Repeat with an unreadable PDF and a scan; neither should look like a successful text check.

For a local preview, run `node server.mjs` and open `http://127.0.0.1:4178/`. The server serves only the generated page; it has no upload route.

| File | Purpose |
| --- | --- |
| `index.html`, `styles.css` | Interface and copy |
| `src/app.mjs` | File lifecycle, worker, previews, clipboard, and DOM |
| `src/review.mjs` | Bounded text and annotation inspection |
| `src/link-region.mjs` | Annotation coordinates clipped to the rendered page |
| `src/text-download.mjs` | UTF-8 text exports and safe download names |
| `src/document-properties.mjs` | Bounded PDF Info/XMP inspection, cancellation, and timeout |
| `build.mjs` | Embedded PDF.js resources, CSP hashes, and ZIP |
| `tests/` | Unit, package, privacy, and browser checks |

PDF.js is pinned in `package-lock.json`. Update it through a dependency PR, rebuild the ZIP, and run all checks. Its license and bundled font/decoder notices are included under **PDF engine and licenses** in the page. The app code uses the repository's MIT license; bundled third-party code retains its own licenses.

## Optional hosting

The same HTML works on a static host. No backend is needed. Do not add analytics or third-party scripts.

For this repository, enable **Settings → Pages → Source: GitHub Actions**, merge the PR, then run **Publish PDF review** from the Actions tab on `main`. The workflow publishes only the generated reviewer, not resume sources or PDFs. Run it again after reviewer updates. Downloaded copies do not update themselves.
