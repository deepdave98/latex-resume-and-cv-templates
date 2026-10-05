# PDF review

Read a resume PDF beside its extracted text. Check where each link points and where it appears on the page.

## Use it

1. [Download the reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip).
2. Unzip it. Open `pdf-review.html` in a current Chrome, Edge, Firefox, or Safari browser.
3. Choose **Open PDF** or drop your file onto the file bar.
4. Read each page and its text. Use **Show on page** to locate a link.
5. Open **Text for application forms** to edit a text copy. **Copy all text** copies that version; **Save .txt** downloads it. **Reset text** restores the extraction. The PDF and per-page text stay unchanged.

The download works offline. The PDF engine, fonts, and decoders are included in the HTML file.

One PDF at a time, up to 20 MiB (20,971,520 bytes) and 20 pages. Password-protected files ask for the password locally.

Opening another file, **Clear file**, and **Reset text** ask before discarding edited text, including edits you have already copied or saved. Cancel keeps the current review. Unchanged text needs no confirmation. Dropping several files also leaves the current review intact.

Reloading or closing the page requests the browser's leave-page warning while text differs from the extraction. Browsers may suppress that warning, so copy or save edits you need before leaving. Nothing is saved automatically.

## Application upload limits

Open **Application upload limits** and enter the maximum pages and file size from the portal's instructions. Leave either blank to skip that check. Limits are inclusive; a file even one byte over is flagged. Nothing is trimmed or compressed.

File size uses decimal MB (1 MB = 1,000,000 bytes); the exact byte count is also shown. Use a whole number for pages and a positive number such as `0.5` for MB. Portals may use different units or additional rules, so these checks do not guarantee acceptance.

Open a revised PDF to check it against the same limits. Clearing, reloading, or closing the page discards the limits; an unreadable or rejected file also resets them. The reviewer's own 20 MiB / 20-page cap still applies.

## What to check

- **Extracted text:** look for missing words, odd symbols, and wrong reading order. Ligatures such as `ﬁ` become ordinary letters for copying.
- **Link destinations:** select **Show on page** beside a destination. Its clickable area is highlighted in the preview so you can compare it with the printed label. **Back to link** returns to that row. Select the same button again to clear the highlight. Destinations remain text only; the tool never follows them or checks whether a website is online. Hidden control characters are shown as escapes. Internal links and unsupported PDF actions are identified separately.
- **Pages without text:** a scan or outlined lettering may look fine but copy nothing. This tool does not run OCR.
- **Pages that appear blank:** this is a preview-based hint, not proof. Very faint content can be missed. A failed preview is never counted as a blank page.
- **Paper size:** each page shows its dimensions and orientation. A4, US Letter, and US Legal are named; other dimensions show as **Custom size**. Compare each page with your application's instructions, especially if you combined PDFs.

Dimensions use the visible page after cropping, rotation, and PDF scale. Values are rounded to 0.1 mm or 0.01 inches; enlarging the preview leaves them unchanged.

Form fields, incomplete extraction, and truncated results get warnings. Check missing text against the original PDF. Extraction can differ between PDF.js, Poppler, and application forms; this is not an ATS test.

Link highlights use the PDF's annotation bounds, not guessed text matches. A PDF can attach a link to a broad area, an image, or no visible label. Missing or off-page bounds get a position warning; a failed preview never gets a highlight. Highlights follow rotated and cropped pages and scale with the preview. Use **Enlarge** to read small labels; **Fit page** restores the full-page view. Neither changes the PDF.

## Privacy

The PDF is read into browser memory. The tool does not upload file contents, names, passwords, or links, and uses no analytics, cookies, browser storage, or service worker. PDF links and scripts are not executed.

The page's Content Security Policy blocks network connections, external scripts, form submission, and plugins. The PDF worker runs locally. Closing, reloading, or clearing the page discards this tool's review. This is not a secure memory wipe, and it cannot control browser extensions or your operating system.

Copying text puts it on your system clipboard. Other apps or clipboard history may retain it. **Save .txt** creates a UTF-8 file in your browser's download location; clearing the review does not delete that file. Exports contain only the text copy, without the reviewer’s warnings or labels. Check it against the PDF, especially if extraction was incomplete. Text edits are limited to 500,100 UTF-16 code units.

If someone hosts this page, their host can receive normal page-request data; it still does not receive your PDF.

## Development

Requires Node.js 24+:

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
| `src/page-size.mjs` | Paper names, dimensions, and orientation from PDF page geometry |
| `src/text-download.mjs` | UTF-8 text exports and safe download names |
| `src/upload-limits.mjs` | Optional page and file-size comparisons |
| `build.mjs` | Embedded PDF.js resources, CSP hashes, and ZIP |
| `tests/` | Unit, package, privacy, and browser checks |

PDF.js is pinned in `package-lock.json`. Update it through a dependency PR, rebuild the ZIP, and run all checks. Its license and bundled font/decoder notices are included under **PDF engine and licenses** in the page. The app code uses the repository's MIT license; bundled third-party code retains its own licenses.

## Optional hosting

The same HTML works on a static host. No backend is needed. Do not add analytics or third-party scripts.

Enable **Settings → Pages → Source: GitHub Actions**, then run **Publish PDF review** from the Actions tab on `main`. It publishes only the reviewer. Rerun it after reviewer updates; downloaded copies do not update themselves.
